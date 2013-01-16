from troia_client.client import TroiaClient
import csv
import datetime
import json
import os
import sys


job_id = "test123"
tc = TroiaClient(sys.argv[1], job_id)
datasets_path = sys.argv[2]
csv_path = sys.argv[3]
    
def drange(start, stop, step):
    r = start
    while r < stop:
        yield r
        r += step

def load_all(path, prefix="testData_", suffix=".txt"):
    r = [list(csv.reader(open(path + s), delimiter='\t'))
            for s in ['/{}goldLabels{}'.format(prefix, suffix), '/{}cost{}'.format(prefix, suffix), '/{}labels{}'.format(prefix, suffix), '/{}objects{}'.format(prefix, suffix)]]
    r[0] = [x[-2:] for x in r[0]]
    return r

def load_aiworker(path, prefix="testData_", suffix=".txt"):
    with open(path + '/{}aiworker{}'.format(prefix, suffix)) as aiworker_file:
        return json.load(aiworker_file)
    
def get_workers_assumed_quality(workers):
    ret = []
    for w in workers:
        avg = 0
        for cat, val in w['confusionMatrix']['matrix'].items():
            avg += val[cat]
        ret.append(avg / len(w['confusionMatrix']['matrix']))
    return ret

def get_workers_real_quality(labels, correct_obj):
    correct_obj_dict = {}
    for obj, cat in correct_obj:
        correct_obj_dict[obj] = cat

    workers_good_answers = {}
    for wor, obj, cat in labels:
        worker_good_answer = workers_good_answers.get(wor, [0, 0])
        if correct_obj_dict[obj] == cat:
            worker_good_answer[0] += 1
        worker_good_answer[1] += 1
        workers_good_answers[wor] = worker_good_answer
    ret = []
    for _, val in workers_good_answers.items():
        ret.append(float(val[0]) / val[1])
    return ret

def get_categories(cost):
    s = set()
    for c1, c2, c in cost:
        s.add(c1)
    return s
    
def aggregate_values(cnt, values, minv=0., maxv=1.):
    ret = {}
    minv = max(round(minv, 1), 0.)
    maxv = min(round(maxv, 1) + 0.1, 1.)
    for i in drange(minv, maxv, (maxv - minv) / cnt):
        ret[i] = 0
    for v in values:
        min_dist = 100
        t = 0
        for r in drange(minv, maxv, (maxv - minv) / cnt):
            if abs(r - v) < min_dist:
                min_dist = abs(r - v)
                t = r
        ret[t] += 1
    return ret

def transform_cost(cost):
    dictt = {}
    for c1, c2, cost_ in cost:
        el = dictt.get(c1, {})
        el[c2] = cost_
        dictt[c1] = el
    return dictt.items()

def compare_object_results(correct_objs, objs):
    cnt = 0
    for k, v in correct_objs:
        if objs[k] == v:
            cnt += 1
            
    return 100 * cnt / len(objs)

ALGORITHMS = ["DS", "MV"]
LABEL_CHOOSING = ["MaxLikelihood", "MinCost", "Soft"]
COST_ALGORITHM = ["ExpectedCost", "MinCost", "MaxLikelihood"]
    
def test_server(tc, gold_labels, cost, labels, correct_objs, **kwargs):
    '''
        @return: tuple of: computation time
    '''
    iterations = kwargs.get("iterations", 30)
    
    tc.status()
    try:
        tc.delete()
    except:
        pass

    t1 = datetime.datetime.now()
    tc.create(transform_cost(cost))
    tc.await_completion(tc.post_gold_data(gold_labels))
    tc.await_completion(tc.post_assigned_labels(labels))
    tc.await_completion(tc.post_evaluation_data(correct_objs))
    tc.await_completion(tc.post_compute(iterations))
    t2 = datetime.datetime.now()
    return (t2 - t1).seconds

def get_data_scores(filename, filemode, first_col_value, esti_func, esti_x, esti_y, eval_func, eval_x, eval_y):
    with open('{}/{}_{}.csv'.format(csv_path, filename, dataset), filemode) as data_cost_file:
        data_cost_writer = csv.writer(data_cost_file, delimiter='\t')
        values = []
        for func, X, Y, name in ((esti_func, esti_x, esti_y, "Estm"), (eval_func, eval_x, eval_y, "Eval")):
            for x in X:
                for y in Y:
                    if filemode == 'w':
                        values.append("{}_{}_{}".format(name, x, y))
                    else:
                        result = tc.await_completion(func(x, y))['result']
                        values.append(round(sum(result.values()) / len(result), 2)) 
        data_cost_writer.writerow([first_col_value] + values)

def get_workers_scores(filename, filemode, first_col_value, esti_func, esti_x, eval_func, eval_x):
    with open('{}/{}_{}.csv'.format(csv_path, filename, dataset), filemode) as data_cost_file:
        data_cost_writer = csv.writer(data_cost_file, delimiter='\t')
        values = []
        for func, X, name in ((esti_func, esti_x, "Estm"), (eval_func, eval_x, "Eval")):  
            for x in X:
                if filemode == 'w':
                    values.append("{}_DS_{}".format(name, x))
                else:
                    result = tc.await_completion(func(x))['result']
                    values.append(round(sum(result.values()) / len(result), 2)) 
        data_cost_writer.writerow([first_col_value] + values)
        
if __name__ == "__main__":
    today = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    timings = []
    for dataset in sys.argv[4:]:
        print "processing ", dataset
        path = "{}/{}/".format(datasets_path, dataset)
        if os.path.exists(path):
            prefix = "{}_".format(dataset)
            data = load_all(path, prefix)
            categories = get_categories(data[1])
            objects = [o for o, c in data[3]]
            workers = load_aiworker(path, prefix)
            kwargs = {}
            timings.append(test_server(tc, *data, **kwargs))
            init = not os.path.exists('{}/data_cost_{}.csv'.format(csv_path, dataset))
            if init:
                get_data_scores("data_cost", "w", "date", tc.get_prediction_data_cost, ALGORITHMS + ['NoVote'], COST_ALGORITHM, tc.get_evaluation_data_cost, ALGORITHMS, LABEL_CHOOSING)
                get_data_scores("data_quality", "w", "date", tc.get_prediction_data_quality, ALGORITHMS, COST_ALGORITHM, tc.get_evaluation_data_quality, ALGORITHMS, LABEL_CHOOSING)
                get_workers_scores("worker_quality", "w", "date", tc.get_prediction_workers_quality, COST_ALGORITHM, tc.get_evaluation_workers_quality, COST_ALGORITHM)
            get_data_scores("data_cost", "ab", today, tc.get_prediction_data_cost, ALGORITHMS + ['NoVote'], COST_ALGORITHM, tc.get_evaluation_data_cost, ALGORITHMS, LABEL_CHOOSING)
            get_data_scores("data_quality", "ab", today, tc.get_prediction_data_quality, ALGORITHMS, COST_ALGORITHM, tc.get_evaluation_data_quality, ALGORITHMS, LABEL_CHOOSING)
            get_workers_scores("worker_quality", "ab", today, tc.get_prediction_workers_quality, COST_ALGORITHM, tc.get_evaluation_workers_quality, COST_ALGORITHM)
        else:
            print path, " doesnt' exists!"
