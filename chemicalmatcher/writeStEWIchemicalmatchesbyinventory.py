#Retrieves all unique flow names from the StEWI flow list, uses SRS web serive to find their SRSname and CAS
import pandas as pd
pd.options.mode.chained_assignment = None
import os

from chemicalmatcher.globals import output_dir,get_SRSInfo_for_substance_name,get_SRSInfo_for_program_list,add_manual_matches, modulepath

stewi_flow_dir = modulepath + '../stewi/output/flow/'

try: flowlists = os.listdir(stewi_flow_dir)
except: print('Directory missing')

all_list_names = pd.DataFrame(columns=["FlowName","FlowID"])

flowlist_cols = {"RCRAInfo":['FlowName','FlowID'],
                 "eGRID": ['FlowName'],
                 "TRI": ['FlowName','FlowID'],
                 "NEI":['FlowName','FlowID'],
                 "GHGRP":['FlowName','FlowID']}

#First loop through flows lists to create a list of all unique flows
for l in flowlists:
    source_name = l[0:l.find("_")]
    source_cols = flowlist_cols[source_name]
    list_names = pd.read_csv(stewi_flow_dir+l,header=0,usecols=source_cols, dtype="str")
    #fix for TRI
    if source_name == 'TRI':
        list_names['FlowID']= list_names['FlowID'].apply(lambda x: x.lstrip('0'))
    list_names['Source'] = source_name
    #Drop duplicates for flowname and ids with multiple compartments
    list_names = list_names.drop_duplicates()
    #Add to others
    all_list_names = pd.concat([all_list_names,list_names], sort = False)

#Drop duplicates from lists with same names
all_list_names.drop_duplicates(inplace=True)

#Reset index after removing flows
all_list_names.reset_index(inplace=True,drop=True)

#Determine whether to use the id or name to query SRS
inventory_query_type = {"RCRAInfo":"list",
                        "TRI":"list",
                        "NEI":"list",
                        "eGRID":"name",
                        "GHGRP":"name"}

#Create a df to store the results
all_lists_srs_info = pd.DataFrame(columns=["FlowName","SRS_ID","SRS_CAS","Source"])
errors_srs = pd.DataFrame(columns=["FlowName","Source","ErrorType"])

#Loop through sources, querying SRS by the query type defined for the source, merge the results with the flows for that inventory
#Store errors in a separate dataframe
sources = list(pd.unique(all_list_names['Source']))
for source in sources:
    # Get df with inventory flows
    inventory_flows = all_list_names[all_list_names['Source'] == source]

    if inventory_query_type[source] == 'list':
    # make sure flowid is a string
        inventory_flows['FlowID'] = inventory_flows['FlowID'].map(str)
    # query SRS to get entire list and then merge with it
        list_srs_info = get_SRSInfo_for_program_list(source)
        #merge this with the original list using FlowID
        list_srs_info = pd.merge(inventory_flows,list_srs_info,left_on='FlowID',right_on='PGM_ID',how='left')
    if inventory_query_type[source] == 'name':

        #For names, query SRS one by one to get results
        list_srs_info = pd.DataFrame(columns=["FlowName", "SRS_ID", "SRS_CAS", "Source"])
        errors_srs = pd.DataFrame(columns=["FlowName", "Source", "ErrorType"])
        # Cycle through names one by one
        for index, row in inventory_flows.iterrows():
            chemical_srs_info = pd.DataFrame(columns=["FlowName", "SRS_ID", "SRS_CAS", "Source"])
            error_srs = pd.DataFrame(columns=["FlowName", "Source", "ErrorDescription"])
            name = row["FlowName"]
            #id = all_list_names["FlowID"][r]
            #source = all_list_names["Source"][r]
            #if inventory_query_type[source] == 'id':
            #    result = get_SRSInfo_for_alternate_id(id, source)
            #if inventory_query_type[source] == 'name':
            result = get_SRSInfo_for_substance_name(name)
            if type(result) is str:
                # This is an error
                error_srs.loc[0, 'FlowName'] = name
                #error_srs.loc[0, 'FlowID'] = id
                error_srs.loc[0, 'Source'] = source
                error_srs.loc[0, 'ErrorDescription'] = result
            else:
                chemical_srs_info = result
                chemical_srs_info.loc[0, "FlowName"] = name
                #chemical_srs_info.loc[0, "FlowID"] = name
                chemical_srs_info.loc[0, "Source"] = source

            errors_srs = pd.concat([errors_srs, error_srs], sort = False)
            list_srs_info = pd.concat([list_srs_info, chemical_srs_info], sort = False)

    all_lists_srs_info = pd.concat([all_lists_srs_info,list_srs_info], sort = False)

#Remove waste code and PGM_ID
all_lists_srs_info = all_lists_srs_info.drop(columns=['PGM_ID'])

#Add in manually found matches
all_lists_srs_info = add_manual_matches(all_lists_srs_info)


#Write to csv
all_lists_srs_info.to_csv(output_dir+'ChemicalsByInventorywithSRS_IDS_forStEWI.csv', index=False)
#errors_srs.to_csv('work/ErrorsSRS.csv',index=False)

#Write flows missing srs_ids to file for more inspection
flows_missing_SRS_ID = all_lists_srs_info[all_lists_srs_info['SRS_ID'].isnull()]
flows_missing_SRS_ID.to_csv('flows_missing_SRS_ID.csv',index=False)
