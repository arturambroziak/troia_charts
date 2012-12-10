import csv
import datetime
import json

from troia_client import TroiaClient

dsas = TroiaClient("http://localhost:8080/GetAnotherLabel/rest/", None)
main_path = "examples/"
job_id = "aatest"

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

def get_workers_estimated_quality(dsas, workers):
    return [1. - dsas.get_worker_cost(job_id, None, str(w['name']))['result'] for w in workers]

def get_data_estimated_quality(dsas, objects, categories):
    dsas.calculate_estimated_cost(job_id)
    obj_qualities = 0.
    for o in objects:
        obj_quality = 1.
        for c in categories:
            obj_quality *= dsas.get_estimated_cost(job_id, o, c)['result']
        obj_qualities += 1. - obj_quality
    return obj_qualities / len(objects)

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

def test_server(dsas, gold_labels, cost, labels, correct_objs, **kwargs):
    '''
        @return: tuple of: labels fitness, computation time
    '''
    iterations = kwargs.get("iterations", 30)
    
    dsas.ping()
    dsas.reset(job_id)

    t1 = datetime.datetime.now()
    dsas.load_categories(transform_cost(cost), job_id)
    dsas.load_gold_labels(gold_labels, job_id)
    dsas.load_worker_assigned_labels(labels, job_id)
    dsas.compute_non_blocking(iterations, job_id)
    dsas.is_computed(job_id)
    t2 = datetime.datetime.now()
    
#    print dsas.print_worker_summary(False, job_id)
    res_objects = dsas.majority_votes(job_id)
    return compare_object_results(correct_objs, res_objects['result']), (t2 - t1).seconds

if __name__ == "__main__":
    today = datetime.date.today()
    timings = []
    fitnesses = []
    data_quality = []
    for dataset in ('small', 'medium', 'big'):
        print dataset
        path = "examples/{}/".format(dataset)
        prefix = "{}_".format(dataset)
        data = load_all(path, prefix)
        categories = get_categories(data[1])
        objects = [o for o, c in data[3]]
        workers = load_aiworker(path, prefix)
        kwargs = {}
        fitness, timing = test_server(dsas, *data, **kwargs)
        fitnesses.append(fitness)
        timings.append(timing)
        print "fitness: {}, timing: {}".format(fitness, timing)
        workers_assumed_quality = get_workers_assumed_quality(workers)
        workers_real_quality = get_workers_real_quality(data[2], data[3])
        workers_estimated_quality = get_workers_estimated_quality(dsas, workers)
        data_quality.append(get_data_estimated_quality(dsas, objects, categories))
        with open('demo/workers_quality_{}.csv'.format(dataset), 'w') as workers_quality_file:
            workers_quality_writer = csv.writer(workers_quality_file, delimiter='\t')
            workers_quality_writer.writerow(['interval', 'assumed', 'real', 'estimated'])
            minv = min((min(workers_assumed_quality), min(workers_estimated_quality), min(workers_real_quality)))
            maxv = max((max(workers_assumed_quality), max(workers_estimated_quality), max(workers_real_quality)))
            vals1 = aggregate_values(10, workers_assumed_quality, minv, maxv)
            vals2 = aggregate_values(10, workers_real_quality, minv, maxv)
            vals3 = aggregate_values(10, workers_estimated_quality, minv, maxv)
            for key in sorted(vals1.iterkeys()):
                workers_quality_writer.writerow([key, vals1[key], vals2[key], vals3[key]])
        
    with open('demo/time.csv', 'ab') as timing_file:
        timings_writer = csv.writer(timing_file, delimiter='\t')
        timings_writer.writerow([today] + timings)

    with open('demo/label_fit.csv', 'ab') as labels_fitness_file:
        labels_fitness_writer = csv.writer(labels_fitness_file, delimiter='\t')
        labels_fitness_writer.writerow([today] + fitnesses)

    with open('demo/data_quality.csv', 'ab') as data_quality_file:
        data_quality_writer = csv.writer(data_quality_file, delimiter='\t')
        data_quality_writer.writerow([today] + data_quality)

