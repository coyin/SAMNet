'''
tfnetwork.py
SAMNet module hadnles transcription factor -mRNA weights


Copyright (c) 2012 Sara JC Gosline
sgosline@mit.edu

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''


import sys,pickle
import os,re
from numpy import log
import networkx
from optparse import OptionParser
#import rpy2.robjects as robjects
import math
import collections

def get_transcriptional_dictionary(transcriptional_network_weight_data,expressed_prot_list=[],addmrna=True,addweight=False,doUpper=True):
    '''
    same as network but keeps dictiory of dictionaries
    if we set addweight to False it is only a dictionary
    '''
    if addweight:
        tdict=collections.defaultdict(dict)
    else:
        tdict=collections.defaultdict(list)

    p300count=0
    for item in transcriptional_network_weight_data:
        #list containing tf mRNA and weight
        list_tf_mrna_weight = item.split('\t')
        #1st element is the transcription factor
        tf = list_tf_mrna_weight[0].strip()
        if tf=='EP300':
            p300count+=1
            continue
#2nd element is mRNA
        mRNA = list_tf_mrna_weight[1].strip()
        if doUpper:
            tf=tf.upper()
            mRNA=mRNA.upper()
#            print mRNA
        #3rd element is weight
        weight =abs(float(list_tf_mrna_weight[2].strip()))
        if weight==0.0:
            weight=0.000001
#        print mRNA.strip()+' weight:'
        #append 'mrna' at end of every mRNA (second element of the list)
        mrna_name = mRNA.strip()
        if len(expressed_prot_list)>0 and mrna_name not in expressed_prot_list:
            continue
        if len(expressed_prot_list)>0 and tf not in expressed_prot_list:
            continue
        if addmrna:
            mrna_name+='mrna'
        if addweight:
            if mrna_name not in tdict[tf].keys():
                tdict[tf][mrna_name]=weight
        else:
            if mrna_name not in tdict[tf]:
                tdict[tf].append(mrna_name)
    print 'Omitted '+str(p300count)+' genes regulated by p300'
    print 'Returning transcriptional dictionary with '+str(len(tdict.keys()))+' TFs'

    return tdict
 
#moved this from response net
def get_transcriptional_network(transcriptional_network_weight_data,addmrna=True,lazy=True,expressed_prot_list=[],doUpper=True,score_thresh=0.0,renormalize=False):
    #initialize graph 
#    print 'upper: '+str(doUpper)
#    transcription_graph = networkx.XDiGraph()
    transcription_graph = networkx.DiGraph()
    if len(transcriptional_network_weight_data)==0:
        print 'Empty TFA file, returning empty graph'
        return transcription_graph
    #get information fro the transcriptional network weight file (this is a list of all transcriptional network data)
    all_edge_weights=[]
    p300counts=0
    p300ids=['EP300','Ep300','icrogid:820620', 'icrogid:4116836']
    for item in transcriptional_network_weight_data:
        #list containing tf mRNA and weight
        list_tf_mrna_weight = item.split('\t')
        #1st element is the transcription factor
        tf = list_tf_mrna_weight[0].strip()
        if tf in p300ids or tf.upper() in p300ids:
            p300counts+=1
            continue
        #2nd element is mRNA
        mRNA = list_tf_mrna_weight[1].strip()
        ##uppercase them both
        if doUpper:
            tf=tf.upper()
            mRNA=mRNA.upper()

        #3rd element is weight
        weight =abs(float(list_tf_mrna_weight[2].strip()))
        if weight<score_thresh:
           # print tf+' : '+mRNA+' interaction ignored due to low weight ('+str(weight)+')'
            next
        if weight==0.0:
            weight=0.000001
        if weight==1.0:
            weight=0.999999
#        print mRNA.strip()+' weight:'
        #append 'mrna' at end of every mRNA (second element of the list)
        mrna_name = mRNA.strip()
        if len(expressed_prot_list)>0 and mrna_name not in expressed_prot_list:
            continue
        if len(expressed_prot_list)>0 and tf not in expressed_prot_list:
            continue
        if addmrna:
            mrna_name+='mrna'
        #make weighted directed edge between the transcription factor and the mRNA
#        print 'Adding edge',tf,'->',mrna_name,'at',str(weight)
        all_edge_weights.append(weight)##add edge for future normalization
        if lazy:
            transcription_graph.add_edge(tf,mrna_name,{'weight':weight})
        else:
            if tf not in transcription_graph.nodes():
                transcription_graph.add_edge(tf,mrna_name,{'weight':weight})
            elif mrna_name not in transcription_graph.successors(tf):
                transcription_graph.add_edge(tf,mrna_name,{'weight':weight})
            elif weight > transcription_graph[tf][mrna_name]['weight']:
                transcription_graph[tf][mrna_name]['weight']=weight
    print 'Removed '+str(p300counts)+' interactions containing p300'
    if renormalize:
        print 'Renormalizing edge weights to be between 0 and 1'
        for edge in transcription_graph.edges_iter():
            old_weight=transcription_graph[edge[0]][edge[1]]['weight']
            new_weight=float(len([x for x in all_edge_weights if x < old_weight]))/float(len(all_edge_weights))
         #   print 'Replacing edge weight of '+str(old_weight)+' with '+str(new_weight)
            transcription_graph[edge[0]][edge[1]]['weight']=new_weight
        
    print 'Returning transcriptional network with '+str(len(transcription_graph.nodes()))+' nodes and '+str(len(transcription_graph.edges()))+' edges'
    return transcription_graph
 
#moved from original responsenet code
#modified by sgosline to include an option to only 
#select up- or down-regulated genes
def get_weights_mRNA_sink(tradatadict, foldtraOrPValue='foldchange',upOrDown='',addMrna=True):
    
    meta_weights_dict={}
    for k in tradatadict.keys():
        weights_sink = {}
        for item in tradatadict[k]:
            fields = item.strip('\r\n').split('\t')
        #mRNA name
            mrna_name = fields[0].strip()

        #fold difference
            folddiff = fields[1].strip()
        #pvalue
            if(len(fields)>2):
                pval = fields[2].strip()
            else:
                pval = 0.0
            if addMrna:
                mname=mrna_name+'mrna'
            else:
                mname=mrna_name
        #user must be able to specify which weight she wants to use (fold difference in expression or p-value)
        #depending on user's choice (foldtra or p-value), make a dictionary of weights between mRNA and sink
            if foldtraOrPValue=='foldchange':
                if upOrDown=='up':
                    weight = float(folddiff)
                elif upOrDown=='down':
                    weight = -float(folddiff)
                else:
                    weight = abs(float(folddiff))
                if(weight >0):
                    weights_sink[mname]= weight 
        #if user did not specify 'foldtra' (so, that she wants to use the fold difference), the p-value will be used
            else:
                weight =-log(float(pval))
                if(upOrDown=='up' and float(folddiff)>0):
                    weights_sink[mname]=weight
                elif(upOrDown=='down' and float(folddiff)<0):
                    weights_sink[mname]=weight
                elif(upOrDown==''):
                    weights_sink[mname]=weight
        meta_weights_dict[k]=weights_sink
    #keys of this dictionary will be all mRNAs from the transcriptional datafile (and their names will contain 'mrna'
    return meta_weights_dict


def filterTfNetwork(tfnetwork,max_degree):
    '''
    This function takes a tf network and filters it to remove high-degree tfs that are likely noise
    '''
    print 'Filtering TF network from '+str(len(tfnetwork.nodes()))+' nodes'
    for node in tfnetwork.nodes():
        if 'mrna' not in node:
            if tfnetwork.degree(node)>max_degree:
                tfnetwork.remove_node(node)
    print 'To '+str(len(tfnetwork.nodes()))+' nodes'
    return tfnetwork
    

####now create some algorithms to assign weights to transcription factors

#method 0: simulate flow algorithm by summing all mrna coming out of each TF
#and multiplying by match score?
def tf_weights_sum(tf_network,mrna_weights):

    tf_weights={}
    tf_with_incoming_weights={}
    tf_with_incoming_norm_weights={}
    tfs=[]
    for i in range(tf_network.number_of_nodes()):
#        if(tf_network.out_degree()[i]>0):
        if(tf_network.out_degree(tf_network.nodes()[i])>0):
            tfs.append(tf_network.nodes()[i])
    
    for t in tfs:
        #sum counts
        diffex_targets=0.0
        diffex_norm=0.0
        for i in tf_network[t]:
            if i in mrna_weights.keys():
                diffex_targets=diffex_targets+mrna_weights[i]#/len(tf_network[t])
                diffex_norm=diffex_norm+mrna_weights[i]/len(tf_network[t])
                
        tf_with_incoming_weights[t]=tf_network.get_edge_data(t,i)['weight']*diffex_targets
        tf_weights[t]=diffex_targets
        tf_with_incoming_norm_weights[t]=tf_network.get_edge_data(t,i)['weight']*diffex_norm

    return tf_with_incoming_norm_weights

###REQUIRES RPY2 MODULE

# #method 1: use hypergeometric to determine TFs that have more than expected diff-ex genes as targets
# def tf_weights_hypergeometric(tf_network,mrna_weights,species='Mouse'):
# #    if(species.lower()=='mouse'):
#     TOTAL_MRNA=20459 #from the mouse affy chip, make this an option in the end
# #    elif(species.lower()=='human'):
# #        TOTAL_MRNA=16857 ##fill in this number, from grimson experiments (mirna)
#     tf_weights={}
#     tfs=[]
#     for i in range(tf_network.number_of_nodes()):
# #        if(tf_network.out_degree()[i]>0):
#         if(tf_network.out_degree(tf_network.nodes()[i])>0):
#             tfs.append(tf_network.nodes()[i])

#     print 'Got '+str(len(tfs))+' tfs'
#     hgvals=[]

#     for t in tfs:
#         #hyperg counts
#         diffex_targets=0
#         non_diffex_targets=0
#         for i in tf_network[t]:
#             if i in mrna_weights.keys():
#                 diffex_targets=diffex_targets+1

#             else:
#                 non_diffex_targets=non_diffex_targets+1

#         #other counts
#         diffex_nontargets=len(mrna_weights.keys())-diffex_targets
#         remainder=TOTAL_MRNA-diffex_nontargets-non_diffex_targets-diffex_targets
#         #now calculate fishers test
# #        print "Calculating pvalue for"+t
#         hgvals.append(t+'\t'+str(diffex_targets)+'\t'+str(non_diffex_targets)+'\t'+str(diffex_nontargets)+'\t'+str(remainder)+'\n')

#         pvalue=robjects.r('fisher.test(matrix(c('+str(diffex_targets)+','+str(non_diffex_targets)+','+str(diffex_nontargets)+','+str(remainder)+"),nrow=2),alternative='greater')$p.value")[0]
#         if(pvalue==0.0):
# #            print "pvalue is 0, setting to pseudocount"
#             pvalue=0.000000001
# #        else:
# #            print 'pvalue is',str(pvalue)
        
#         print "TF "+t+' has pvalue of '+str(pvalue)+' and weight of '+str(-log(pvalue))
        
#         if(log(pvalue)==0.0 or log(pvalue)==-0.0):
#         #    print 'log of '+str(pvalue)+' is 0.0, setting to pseudo count'
#             tf_weights[t]=0.000000001
#         else:
#             tf_weights[t]=-log(pvalue)

#     open('hg_pvals.txt','w').writelines(hgvals)
#     return tf_weights


#method 3: use any set of arbitrary weights on transcription factors
def use_own_weights(tf_weight_file,up_or_down=''):
    '''
    Allows for the input of weighted file of TFs with two columns
    First column is TF identifier and second column is weight
    '''
    tf_weight={}
    for line in open(tf_weight_file,'r').readlines():
        arr=re.split('\t',line.strip())
        prot=arr[0]
        weight=arr[1]#ignore everything else
        if up_or_down=='up':
            w=float(weight)
        elif up_or_down=='down':
            w=-float(weight)
        else:
            w=abs(float(weight))
        if w>0:    
            tf_weight[prot]=w

    return tf_weight

#print out weight file
def print_weight_file(tf_weights,outputname):
    wfile=open(outputname+'_tf_weights.txt','w')
    for t in tf_weights.keys():
        wfile.write(t+'\t'+str(tf_weights[t])+'\n')
    wfile.close()




def main():##this is mainly to test, hopefully this will be called from responsenet code
    #PARSING PARAMETERS
    parser = OptionParser()
    parser.add_option("--tra",type='string',dest='trafile',help='List of mrna differentially expressed in response to stimulus.  Tab-delmited file of mrna in the first column, fold change in the second column, and p-value in the third column. If using regression need all mRNA, not just those that are differentially expressed')
    parser.add_option("--tfmrna",type='string',dest='tf_mrna_file',help='Tab-delimited file of transcription factor to mrna targets from match or some other program')
    parser.add_option("--foldtraorp", type="string", default="pvalue", dest="foldtra", help="OPTIONAL: whether to use fold difference or p-value for weights between mRNA and sink. Write 'foldtra' for fold difference, or 'pvalue' for p-value. Default is 'pvalue'")
    parser.add_option("--regressionorhyperg",type='string',default='hyperg',dest='regression_or_hyperg',help="OPTIONAL: whether to not to use regression or hyperg to determin tf weights. Default is 'hyperg'")
    parser.add_option("--output",type='string',dest='outputfile',help='Output file prefix')

    #that's it for options, now to parse them
    (options, args) = parser.parse_args()
    
    #trying to preserve variable names from responsenet code
    trafile=open(options.trafile,'r') #can't handle multipe files without responsenet code
    tradata=trafile.readlines()
    tweightfile=open(options.tf_mrna_file,'r')
    tf_mrna_weights_data=tweightfile.readlines()
    
    #get the transcriptional network
    graph_tr = get_transcriptional_network(tf_mrna_weights_data)

    #use this method to get weighted list of differentially expressed mrna and weights
    #(if we can use them)
    weights_mRNA_to_sink = get_weights_mRNA_sink(tradata,options.foldtra)

    #choose a method of determining weights
    if(options.regression_or_hyperg=='hyperg'):
        final_tf_weights=tf_weights_hypergeometric(graph_tr,weights_mRNA_to_sink)
    elif(options.regression_or_hyperg=='regression'):
        final_tf_weights=tf_weights_regression(graph_tr,weights_mRNA_to_sink)
    else:
        final_tf_weights={}

    print_weight_file(final_tf_weights,options.outputfile)
    
    

if __name__=='__main__':
    main()
