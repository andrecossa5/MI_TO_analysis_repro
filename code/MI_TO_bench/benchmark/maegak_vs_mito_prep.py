"""
Benchmark maegatk vs mito_preprocessing, MI_TO vs vanilla, at various filtering parameters.
"""

import os
from itertools import product
from mito_utils.utils import *
from mito_utils.preprocessing import *
from mito_utils.phylo import *
from mito_utils.clustering import custom_ARI
from sklearn.metrics import normalized_mutual_info_score


##


# Args
sample = 'MDA_PT'
path_meta = '/Users/IEO5505/Desktop/MI_TO/MI_TO_analysis_repro/data/MI_TO_bench/cells_meta.csv'
path_dbSNP = '/Users/IEO5505/Desktop/MI_TO/MI_TO_analysis_repro/data/MI_TO_bench/miscellanea/dbSNP_MT.txt'
path_REDIdb = '/Users/IEO5505/Desktop/MI_TO/MI_TO_analysis_repro/data/MI_TO_bench/miscellanea/REDIdb_MT.txt'

# Parameter space
grid = list(
    product(
        ['mito_preprocessing', 'maegatk'],  # pp_method
        np.linspace(.005, .05, 5),          # af_confident_detection
        np.arange(1, 3+1, 1),               # min_n_confidently_detected
        np.linspace(1, 3, 5),               # min_mean_AD_in_positives
        [1,2],                              # min_AD 
        ['vanilla', 'MI_TO']                # bin_method 
    )
)
ntot = len(grid)


##


def main():

    metrics = {}
    combos = {}

    for i, combo in enumerate(grid):

        try:
            
            job = f'job_{i}'
            logging.info(f'{job}/{ntot}')
            (
                pp_method, af_confident_detection, 
                min_n_confidently_detected, min_mean_AD_in_positives, min_AD, bin_method

            ) = combo

            logging.info(f'{combo}')

            metric = 'jaccard' if bin_method == 'vanilla' else 'custom_MI_TO_jaccard'
            path_ch_matrix = f'/Users/IEO5505/Desktop/MI_TO/MI_TO_analysis_repro/data/MI_TO_bench/AFMs/{pp_method}/{sample}/'

            afm = sc.read(os.path.join(path_ch_matrix, 'afm.h5ad'))
            afm = filter_cells(afm, cell_filter='filter2')
            afm = filter_afm(
                afm,
                min_cell_number=10,
                lineage_column='GBC',
                filtering_kwargs={
                    'min_cov' : 10,
                    'min_var_quality' : 30,
                    'min_frac_negative' : 0.2,
                    'min_n_positive' : 5,
                    'af_confident_detection' : af_confident_detection,
                    'min_n_confidently_detected' : min_n_confidently_detected,
                    'min_mean_AD_in_positives' : min_mean_AD_in_positives,       # 1.25,
                    'min_mean_DP_in_positives' : 25
                },
                binarization_kwargs={
                    't_prob':.75, 't_vanilla':0, 'min_AD':min_AD, 'min_cell_prevalence':.2
                },
                bin_method=bin_method,
                tree_kwargs={'metric':metric, 'solver':'NJ'},
                path_dbSNP=path_dbSNP, 
                path_REDIdb=path_REDIdb,
                spatial_metrics=True,
                compute_enrichment=True,
                max_AD_counts=2
            )

            tree = build_tree(afm, precomputed=True)
            d = afm.uns['dataset_metrics']
            d['n_GBC'] = tree.cell_meta['GBC'].nunique()
            d['corr_dist'] = calculate_corr_distances(tree)
            d['AUPRC'] = distance_AUPRC(afm.obsp['distances'].A, afm.obs['GBC'])

            if afm.shape[1]>=20:
                tree, _, _ = cut_and_annotate_tree(tree)
                d['ARI'] = custom_ARI(tree.cell_meta['GBC'], tree.cell_meta['MT_clone'])
                d['NMI'] = normalized_mutual_info_score(tree.cell_meta.dropna()['GBC'], tree.cell_meta.dropna()['MT_clone'])

            metrics[job] = d
            combos[job] = combo

        except Exception as e:
            continue

    ##


    # Save
    with open('/Users/IEO5505/Desktop/MI_TO/MI_TO_analysis_repro/results/MI_TO_bench/benchmark/metrics.pickle', 'wb') as f:
        pickle.dump(metrics, f)
    with open('/Users/IEO5505/Desktop/MI_TO/MI_TO_analysis_repro/results/MI_TO_bench/benchmark/combos.pickle', 'wb') as f:
        pickle.dump(combos, f)


    ##


# Run
if __name__ == "__main__":
    main()




