import sys
import time
import csv
import datetime

from troia_client import TroiaClient

dsas = TroiaClient("http://localhost:8080/GetAnotherLabel/rest/", None)
main_path = "examples/"

def load_all(path, prefix="testData_", suffix=".txt"):
    r = [list(csv.reader(open(path + s), delimiter='\t'))
            for s in ['/{}goldLabels{}'.format(prefix, suffix), '/{}cost{}'.format(prefix, suffix), '/{}labels{}'.format(prefix, suffix), '/{}objects{}'.format(prefix, suffix)]]
    r[0] = [x[-2:] for x in r[0]]
    return r

def transform_cost(cost):
    dictt = {}
    for c1, c2, cost_ in cost:
        el = dictt.get(c1, {})
        el[c2] = cost_
        dictt[c1] = el
    return dictt.items()

def load_objects():
    pass

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
    job_id = "123"
    iterations = kwargs.get("iterations", 100)
    
    dsas.ping()
    dsas.reset(job_id)

    t1 = datetime.datetime.now()
    dsas.load_categories(transform_cost(cost), job_id)
    dsas.load_gold_labels(gold_labels, job_id)
    dsas.load_worker_assigned_labels(labels, job_id)
    dsas.compute_non_blocking(iterations, job_id)
    dsas.is_computed(job_id)
    t2 = datetime.datetime.now()
    
#        print dsas.print_worker_summary(False, job_id)
    res_objects = dsas.majority_votes(job_id)
    return compare_object_results(correct_objs, res_objects['result']), (t2 - t1).seconds

if __name__ == "__main__":
    data = load_all(sys.argv[1])
    today = datetime.date.today()
    with open('demo/label_fit.csv', 'ab') as labels_fitness_file, open('demo/time.csv', 'ab') as timing_file:
        labels_fitness_writer = csv.writer(labels_fitness_file, delimiter='\t')
        timings_writer = csv.writer(timing_file, delimiter='\t')
#        for i in xrange(1, 15, 14):
#            kwargs = {"iterations": i}
        kwargs = {}
        fitness, timing = test_server(dsas, *data, **kwargs)
        labels_fitness_writer.writerow([today, fitness])
        timings_writer.writerow([today, timing])
