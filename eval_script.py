#!/usr/bin/env python2.7
from client.gal import TroiaClient
import csv
import datetime
import os
import sys

def drange(start, stop, step):
    r = start
    while r < stop:
        yield r
        r += step

def load_all(path):
    r = [list(csv.reader(open(path + s), delimiter='\t'))
            for s in ['/goldLabels', '/cost', '/labels', '/objects']]
    r[0] = [x[-2:] for x in r[0]]
    return r

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
        el = dictt.get(c1, [])
        el.append({'categoryName': c2,
                   'value': cost_})
        dictt[c1] = el
    return dictt.items()

def compare_object_results(correct_objs, objs):
    cnt = 0
    for k, v in correct_objs:
        if objs[k] == v:
            cnt += 1

    return 100 * cnt / len(objs)

ALGORITHMS = ["BDS", "BMV"]
LABEL_CHOOSING = ["MaxLikelihood", "MinCost", "Soft"]
COST_ALGORITHM = ["ExpectedCost", "MinCost", "MaxLikelihood"]

def create_server(tc, alg, gold_labels, cost, labels, correct_objs, **kwargs):
    '''
        @return: computation time
    '''
    iterations = kwargs.get("iterations", 30)

    categories = list(set(a for a, _, _ in cost))
    category_priors = [{"categoryName": c, "value": 1. / len(categories)} for c in categories]
    tc.create(categories, iterations=iterations, algorithm=alg, categoryPriors=category_priors)
    tc.await_completion(tc.post_gold_data(gold_labels))
    tc.await_completion(tc.post_assigned_labels(labels))
    tc.await_completion(tc.post_evaluation_objects(correct_objs))
    tc.await_completion(tc.post_compute())
    return tc

def write_scores(path, filename, dataset, values):
    def diffrent_values(a, b):
        for s1, s2 in zip(a, b):
            if float(s1) != float(s2):
                return True
        return False
    diff = False
    with open('{}/{}_{}.csv'.format(path, filename, dataset), "r") as csv_file:
        if diffrent_values(csv_file.readlines()[-1].split()[2:], values[1:]):
            diff = True
    if diff:
        with open('{}/{}_{}.csv'.format(path, filename, dataset), "ab") as csv_file:
            data_cost_writer = csv.writer(csv_file, delimiter='\t')
            data_cost_writer.writerow(values)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print "server_path, datasets_path, csv_path, d1, d2, d2.."
    else:
        settings = [
             {'filename': 'data_cost',
              'esti_function_name': 'get_estimated_objects_cost',
              'eval_function_name': 'get_evaluated_objects_cost',
              'esti_algorithms': ALGORITHMS + ['NoVote'],
              'esti_params': COST_ALGORITHM,
              'eval_algorithms': ALGORITHMS,
              'eval_params': LABEL_CHOOSING},
             {'filename': 'data_quality',
              'esti_function_name': 'get_estimated_objects_quality',
              'eval_function_name': 'get_evaluated_objects_quality',
              'esti_algorithms': ALGORITHMS,
              'esti_params': COST_ALGORITHM,
              'eval_algorithms': ALGORITHMS,
              'eval_params': LABEL_CHOOSING},
             {'filename': 'worker_quality',
              'esti_function_name': 'get_estimated_workers_quality',
              'eval_function_name': 'get_evaluated_workers_quality',
              'esti_algorithms': ["BDS"],
              'esti_params': COST_ALGORITHM,
              'eval_algorithms': ["BDS"],
              'eval_params': COST_ALGORITHM}]
        datasets_path = sys.argv[2]
        csv_path = sys.argv[3]
        today = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

        for dataset in sys.argv[4:]:
            print "processing ", dataset
            path = "{}/{}/".format(datasets_path, dataset)
            tc = {}
            if os.path.exists(path):
                data = load_all(path)
                categories = get_categories(data[1])
                objects = [o for o, c in data[3]]
                kwargs = {}
                for a in ALGORITHMS:
                    tc[a] = create_server(TroiaClient(sys.argv[1]), a, *data, **kwargs)
                
                for s in settings:
                    values = [today]
                    for func, A, P, name in ((s['esti_function_name'], s['esti_algorithms'], s['esti_params'], "Estm"), 
                                             (s['eval_function_name'], s['eval_algorithms'], s['eval_params'], "Eval")):
                        for alg in A:
                            for param in P:
                                if alg in tc:
                                    result = tc[alg].await_completion(getattr(tc[alg], func)(param))['result']
                                    values.append(round(sum((v['value'] if v['value'] != u'NaN' else 0 for v in result)) / len(result), 2))
                                else:
                                    values.append(0)
                    write_scores(csv_path, s['filename'], dataset, values)
            else:
                print path, " doesnt' exists!"
