from tqdm.auto import tqdm
import collections
import csv
import math
import pickle

PBAR = None


class Optimizer:
    def __init__(self, cerebro, strategy, generator, *args):
        self.cerebro = cerebro

        total_testcase = sum(1 for _ in generator(*args))

        global PBAR
        PBAR = tqdm(smoothing=0.05, desc='Optimization', total=total_testcase)

        self.cerebro.optstrategy(strategy, optimization_dict=generator(*args))
        self.cerebro.optcallback(cb=self.bt_opt_callback)

    def start(self):
        return self.cerebro.run(runonce=False, stdstats=False)

    def bt_opt_callback(self, cb):
        global PBAR
        PBAR.update()


def flatten_dict(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.abc.MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def save_strats(strats, output_path, chunk_size=512):
    with open(f'{output_path}.csv', 'w', newline='', encoding='utf-8') as w:
        writer = csv.writer(w)
        header_row = list(strats[0].p._getkeys())

        for name_of_analyzer, analyzer in zip(strats[0].analyzers._names, strats[0].analyzers._items):
            if name_of_analyzer in ('tradeanalyzer', 'transactions'):
                continue

            else:
                rets_dict = analyzer.get_analysis()
                rets_dict = flatten_dict(rets_dict)
                for name_of_ret in rets_dict.keys():
                    header_row += [f'{name_of_analyzer}_{name_of_ret}']

        writer.writerow(header_row)

        for strat in strats:
            row = strat.p._getvalues()

            for name_of_analyzer, analyzer in zip(strat.analyzers._names, strat.analyzers._items):
                if name_of_analyzer in ('tradeanalyzer', 'transactions'):
                    continue

                else:
                    rets_dict = analyzer.get_analysis()
                    rets_dict = flatten_dict(rets_dict)
                    for ret in rets_dict.values():
                        row += [ret]

            writer.writerow(row)

    for i in range(math.ceil(len(strats) / chunk_size)):
        pickle.dump(strats[i * chunk_size: (i + 1) * chunk_size], open(f'{output_path}_{i * chunk_size}_{(i + 1) * chunk_size - 1}.pickle', 'wb'))
