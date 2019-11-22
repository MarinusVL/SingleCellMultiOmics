#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import singlecellmultiomics
from singlecellmultiomics.molecule import MoleculeIterator, NlaIIIMolecule
from singlecellmultiomics.fragment import NLAIIIFragment
import pysam
import collections
import pysamiterators
import pandas as pd
import seaborn as sns
import numpy as np
import re
import sklearn.ensemble

def bin_to_sort_value(chrom):
    chrom = chrom.replace('chr','')
    try:
        if '_' in chrom:

            int_chrom = int( chrom.split('_')[0] )

        elif chrom=='X':
            int_chrom=99
        else:
            int_chrom=int(chrom)
    except Exception as e:
            return ( (999, chrom ) )
    return (int_chrom, chrom )

if __name__=='main':
    argparser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, description="""Correct count table for GC, site abundance and others""")
    argparser.add_argument('-reads' , required=True)
    argparser.add_argument('-umis' , required=True)
    argparser.add_argument('-no-change-regions', required=True)
    argparser.add_argument('-ref', required=True)
    args = argparser.parse_args()

    no_change_regions = args.no_change_regions.split(',')

    df_reads = pd.read_pickle( args.pickle_reads ).sum(level=[1], axis=0)
    df_umis = pd.read_pickle( args.pickle_umis ).sum(level=[1], axis=0)

    df_reads = df_reads.reindex( sorted(df_reads.columns, key=lambda a: (bin_to_sort_value(a[0]),a[1]) ) , axis=1 )
    df_umis = df_umis.reindex( sorted(df_umis.columns, key=lambda a: (bin_to_sort_value(a[0]),a[1]) ) , axis=1 )

    reference = pysamiterators.CachedFasta(pysam.FastaFile(args.ref))

    # Calculate reference statistics
    ref_stats = collections.defaultdict(dict)
    for chrom, bin_idx in df_reads:
        bin_seq = reference.fetch(chrom, bin_idx*bin_size, (1+bin_idx)*bin_size).upper()
        base_obs = collections.Counter(bin_seq)

        ref_stats[(chrom, bin_idx)]['BASES'] = sum( base_obs.values() )
        if ref_stats[(chrom, bin_idx)]['BASES'] >0:
            ref_stats[(chrom, bin_idx)]['GC'] = (base_obs['G']+base_obs['C'])/ref_stats[(chrom, bin_idx)]['BASES']
        else:
            ref_stats[(chrom, bin_idx)]['GC'] = np.nan # add the mean here later
        ref_stats[(chrom, bin_idx)]['SITE_COUNT'] = bin_seq.count('CATG')

        frag_sizes = np.diff( [m.start() for m in re.finditer('CATG', bin_seq)])
        ref_stats[(chrom, bin_idx)]['FRAG>40'] = np.sum(frag_sizes>40)
        ref_stats[(chrom, bin_idx)]['FRAG>70'] = np.sum(frag_sizes>70)
        ref_stats[(chrom, bin_idx)]['MEAN_FS'] = np.mean(frag_sizes)

    regressor = sklearn.ensemble.RandomForestRegressor(n_estimators=100, n_jobs=8)

    X = rdf[no_change_regions].T
    y = df_umis[no_change_regions].sum(0)*2
    regressor.fit(X,y)
    reduced = (df_umis/regressor.predict(rdf.T)).fillna(0)