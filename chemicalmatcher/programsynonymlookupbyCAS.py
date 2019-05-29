#This files takes in a csv file with one formatted CAS number per row and returns synonym names from EPA's programs
# of interest using the SRS web service. It writes this out to a csv file
import requests
import pandas as pd
import json
from chemicalmatcher.globals import base, config

#datapath = 'chemicalmatcher/data/'
#outputpath = 'chemicalmatcher/output/'
#outputfilename = 'examplesynonymnlistfromCASlist.csv'


#SRS web service docs at https://cdxnodengn.epa.gov/cdx-srs-rest/
#Base URL for queries
queries = config()['databases']['SRS']['queries']
caslistprefix = queries['caslistprefix']
sep= queries['sep']# This is the code for a pipe seperator required between CAS numbers

#import list of CAS
#filename = 'examplecaslist.csv'
#caslist = pd.read_csv(datapath+filename,header=None)
#caslist_unique = list(pd.unique(caslist[0]))

def programsynonymlookupbyCAS(cas_list,inventories_of_interest):
    caslist_for_query  = ''
    index_of_last = len(cas_list)-1
    for cas in cas_list[:index_of_last]:
        caslist_for_query = caslist_for_query+cas+sep
    #add on last CAS
    caslist_for_query = caslist_for_query + cas_list[index_of_last]

    #perform query
    url = base+caslistprefix+caslist_for_query
    chemicallistresponse = requests.get(url)
    chemicallistjson = json.loads(chemicallistresponse.text)

    inventory_to_program_of_interest_mapping = {
    'TRI':'Toxics Release Inventory Program System',
    'NEI':'Emissions Inventory System',
    'DMR':'Permit Compliance System',
    }

    #Invert this dictionary for later use in lookups
    program_of_interest_to_inventory_mapping = {v: k for k, v in inventory_to_program_of_interest_mapping.items()}

    lists_of_interest = []
    for i in inventories_of_interest:
        lists_of_interest.append(inventory_to_program_of_interest_mapping[i])

    #Create a list to store the results
    all_chemical_list = []

    #Loop through each chemical in the response
    #Get the cas and then the synonyms for the programs of interest
    #add each one to a dictionary
    for chemical in chemicallistjson:
       #get cas
       chemicaldict = {}
       chemicaldict['CAS'] = chemical['currentCasNumber']
       #get synonyms
       df = pd.DataFrame(chemical['synonyms'])
       dfwithlistsofinterest = df[df['listName'].isin(lists_of_interest)]

       for l in lists_of_interest:
           record = dfwithlistsofinterest[dfwithlistsofinterest["listName"] == l]["synonymName"]
           list_acronym = program_of_interest_to_inventory_mapping[l]
           if len(record.values) == 0:
               #no synonym is present
               chemicaldict[list_acronym] = None
           else:
               syn = record.values[0]
               chemicaldict[list_acronym] = syn
       all_chemical_list.append(chemicaldict)

    #Write it into a df
    all_chemical_synonyms = pd.DataFrame(all_chemical_list)

    #Write to csv
    #all_chemical_synonyms.to_csv(outputpath+outputfilename, index=False)

    return all_chemical_synonyms
