
# coding: utf-8

# # Download Publicly Available Hematopoietic Dataset
# 
# **Gregory Way, 2018**
# 
# Here, I download [GSE24759](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE24759) which is associated with [Novershtern et al. 2011](https://doi.org/10.1016/j.cell.2011.01.004).
# 
# This dataset includes 211 samples consisting of 38 distinct hematopoietic states in various stages of differentiation.
# 
# We hypothesized that our constructed feature identified through our interpret compression approach would have higher activation patterns in Monocytes.

# In[1]:


import os
import csv
import pandas as pd
from sklearn import preprocessing

from scripts.utils import download_geo


# In[2]:


base_url = 'ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE24nnn/GSE24759/suppl/'
name = 'GSE24759_data.sort.txt.gz'
directory = 'download'


# In[3]:


download_geo(base_url, name, directory)


# In[4]:


path = 'download/GSE24759_data.sort.txt.gz'
get_ipython().system(' sha256sum $path')


# ## Process the Data

# In[5]:


# Load Additional File 3
geo_df = pd.read_table(path)

print(geo_df.shape)
geo_df.head(2)


# ## Update Gene Names

# In[6]:


# Load curated gene names from versioned resource 
commit = '721204091a96e55de6dcad165d6d8265e67e2a48'
url = 'https://raw.githubusercontent.com/cognoma/genes/{}/data/genes.tsv'.format(commit)
gene_df = pd.read_table(url)

# Only consider protein-coding genes
gene_df = (
    gene_df.query("gene_type == 'protein-coding'")
)

symbol_to_entrez = dict(zip(gene_df.symbol,
                            gene_df.entrez_gene_id))


# In[7]:


# Add alternative symbols to entrez mapping dictionary
gene_df = gene_df.dropna(axis='rows', subset=['synonyms'])
gene_df.synonyms = gene_df.synonyms.str.split('|')

all_syn = (
    gene_df.apply(lambda x: pd.Series(x.synonyms), axis=1)
    .stack()
    .reset_index(level=1, drop=True)
)

# Name the synonym series and join with rest of genes
all_syn.name = 'all_synonyms'
gene_with_syn_df = gene_df.join(all_syn)

# Remove rows that have redundant symbols in all_synonyms
gene_with_syn_df = (
    gene_with_syn_df
    
    # Drop synonyms that are duplicated - can't be sure of mapping
    .drop_duplicates(['all_synonyms'], keep=False)

    # Drop rows in which the symbol appears in the list of synonyms
    .query('symbol not in all_synonyms')
)


# In[8]:


# Create a synonym to entrez mapping and add to dictionary
synonym_to_entrez = dict(zip(gene_with_syn_df.all_synonyms,
                             gene_with_syn_df.entrez_gene_id))

symbol_to_entrez.update(synonym_to_entrez)


# In[9]:


# Load gene updater
commit = '721204091a96e55de6dcad165d6d8265e67e2a48'
url = 'https://raw.githubusercontent.com/cognoma/genes/{}/data/updater.tsv'.format(commit)
updater_df = pd.read_table(url)
old_to_new_entrez = dict(zip(updater_df.old_entrez_gene_id,
                             updater_df.new_entrez_gene_id))


# In[10]:


# Update the symbol column to entrez_gene_id
geo_map = geo_df.A_Desc.replace(symbol_to_entrez)
geo_map = geo_map.replace(old_to_new_entrez)
geo_df.index = geo_map
geo_df.index.name = 'entrez_gene_id'
geo_df = geo_df.drop(['A_Name', 'A_Desc'], axis='columns')
geo_df = geo_df.loc[geo_df.index.isin(symbol_to_entrez.values()), :]


# ## Scale Data and Output to File

# In[11]:


# Scale RNAseq data using zero-one normalization
geo_scaled_zeroone_df = preprocessing.MinMaxScaler().fit_transform(geo_df.transpose())
geo_scaled_zeroone_df = (
    pd.DataFrame(geo_scaled_zeroone_df,
                 columns=geo_df.index,
                 index=geo_df.columns)
    .sort_index(axis='columns')
    .sort_index(axis='rows')
)

geo_scaled_zeroone_df.columns = geo_scaled_zeroone_df.columns.astype(str)
geo_scaled_zeroone_df = geo_scaled_zeroone_df.loc[:, ~geo_scaled_zeroone_df.columns.duplicated(keep='first')]

os.makedirs('data', exist_ok=True)

geo_scaled_zeroone_df.columns = geo_scaled_zeroone_df.columns.astype(str)
geo_scaled_zeroone_df = geo_scaled_zeroone_df.loc[:, ~geo_scaled_zeroone_df.columns.duplicated(keep='first')]

file = os.path.join('data', 'GSE24759_processed_matrix.tsv.gz')
geo_scaled_zeroone_df.to_csv(file, sep='\t', compression='gzip')

geo_scaled_zeroone_df.head()


# ## Process Cell-Type Classification
# 
# Data acquired from Supplementary Table 1 of [Novershtern et al. 2011](https://doi.org/10.1016/j.cell.2011.01.004)

# In[12]:


cell_class = {
    # Hematopoietic Stem Cells
    'HSC1': ['HSC', 'Non Monocyte'],
    'HSC2': ['HSC', 'Non Monocyte'],
    'HSC3': ['HSC', 'Non Monocyte'],
    
    # Myeloid Progenitors
    'CMP': ['Myeloid', 'Non Monocyte'],
    'MEP': ['Myeloid', 'Non Monocyte'],
    'GMP': ['Myeloid', 'Non Monocyte'],
    
    # Erythroid Populations
    'ERY1': ['Erythroid', 'Non Monocyte'],
    'ERY2': ['Erythroid', 'Non Monocyte'],
    'ERY3': ['Erythroid', 'Non Monocyte'],
    'ERY4': ['Erythroid', 'Non Monocyte'],
    'ERY5': ['Erythroid', 'Non Monocyte'],
    
    # Megakaryocytic Populations
    'MEGA1': ['Megakaryocytic', 'Non Monocyte'],
    'MEGA2': ['Megakaryocytic', 'Non Monocyte'],
    
    # Granulocytic Populations
    'GRAN1': ['Granulocytic', 'Non Monocyte'],
    'GRAN2': ['Granulocytic', 'Non Monocyte'],
    'GRAN3': ['Granulocytic', 'Non Monocyte'],
    
    # Monocyte Population (Note MONO1 is a CFU-M)
    'MONO1': ['Monocyte', 'Non Monocyte'],
    'MONO2': ['Monocyte', 'Monocyte'],
    
    # Basophil Population
    'BASO1': ['Basophil', 'Non Monocyte'],
    
    # Eosinophil Population
    'EOS2': ['Eosinophil', 'Non Monocyte'],
    
    # B Lymphoid Progenitors
    'PRE_BCELL2': ['B Lymphoid Progenitor', 'Non Monocyte'],
    'PRE_BCELL3': ['B Lymphoid Progenitor', 'Non Monocyte'],
    
    # Naive Lymphoid Progenitors
    'BCELLA1': ['Naive Lymphoid', 'Non Monocyte'],
    'TCELLA6': ['Naive Lymphoid', 'Non Monocyte'],
    'TCELLA2': ['Naive Lymphoid', 'Non Monocyte'],
    
    # Differentiated B Cells
    'BCELLA2': ['Differentiated B Cell', 'Non Monocyte'],
    'BCELLA3': ['Differentiated B Cell', 'Non Monocyte'],
    'BCELLA4': ['Differentiated B Cell', 'Non Monocyte'],
    
    # Differentiated T Cells
    'TCELLA7': ['Differentiated T Cell', 'Non Monocyte'],
    'TCELLA8': ['Differentiated T Cell', 'Non Monocyte'],
    'TCELLA1': ['Differentiated T Cell', 'Non Monocyte'],
    'TCELLA3': ['Differentiated T Cell', 'Non Monocyte'],
    'TCELLA4': ['Differentiated T Cell', 'Non Monocyte'],
    
    # Natural Killer Population
    'NKA1': ['NK Cell', 'Non Monocyte'],
    'NKA2': ['NK Cell', 'Non Monocyte'],
    'NKA3': ['NK Cell', 'Non Monocyte'],
    'NKA4': ['NK Cell', 'Non Monocyte'],
    
    # Dendritic Cell
    'DENDA1': ['Dendritic', 'Non Monocyte'],
    'DENDA2': ['Dendritic', 'Non Monocyte'],
}


# In[13]:


# Write data to file
cell_class_df = (
    pd.DataFrame.from_dict(cell_class)
    .transpose()
    .reset_index()
    .rename(columns={'index': 'label', 0: 'classification', 1: 'monocyte'})
)

cell_class_df.head()


# In[14]:


file = os.path.join('results', 'cell-type-classification.tsv')
cell_class_df.to_csv(file, sep='\t', index=False)

