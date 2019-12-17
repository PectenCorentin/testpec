#Automatic_review.py script runs a code review checks on the files which are provided as input by user via google forms

#####Update#####
# Modified by: Pavan on 10/12/2019 , refining the checks for readme,unitest and jenkin files and removal of unwanted code

import argparse
import re
import os
import sys
import smtplib, ssl
from pecten_utils import miscellaneous as misc

from datetime import datetime, timedelta, time
from langdetect import detect
from time import sleep
from difflib import SequenceMatcher

import pandas as pd
import numpy as np
import nltk

import gspread
from oauth2client.service_account import ServiceAccountCredentials


from pecten_utils import miscellaneous as misc
from pecten_utils.Storage import Storage
from pecten_utils.relevant_text_classifier import Relevant_Text_Classifier 
from pecten_utils.TaggingUtils import TaggingUtils
from pecten_utils.BigQueryLogsHandler import BigQueryLogsHandler
from pecten_utils.duplication_handler import DuplicationHandler

import dateutil.parser
import logging

from pathlib import Path


def main(args):
    
    args.misc = misc
    args.datasets = misc.get_dataset_names(args.environment)
    args.storage = Storage(google_key_path=args.google_key_path)
    sys.path.insert(0, args.python_path)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = BigQueryLogsHandler(args.storage, args)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    args.logger = logger
    #args.parameters = get_storage_details(args)'''
    param_table = "PARAM_CREDENTIALS"
    param_list = ["EMAIL", "PASSWORD"]
    parameters = misc.get_parameters(connection_string= args.param_connection_string, table= param_table, column_list= param_list)
    gmail_user = parameters["EMAIL"]
    gmail_pwd = parameters["PASSWORD"]
    code_result = True
    count_checks = 0
    automatic_review(args,gmail_user,gmail_pwd)
    return code_result

# Function to check for Table used in script is as per folder
def checkForMatch_folderName_SQLTableName(df):
    table_match_result = {}
    for index, row in df.iterrows():
    # print(, row['param_table'])
        if '_'in row['Folder Name']:
            count_checks += 1
            split_string = (row['Folder Name'].split('_'))
            for str in split_string:
                if str in row['param_table'].lower():
                    table_match_result[row['Email ID']] = " "
                    break
                else:
                    str_tableMatch= row['param_table'] + " Table name and " + row['Folder Name'], " folder name mismatch"
                    table_match_result[row['Email ID']] = str_tableMatch
                    code_result = False;
                    print (row['param_table'], "Table name and", row['Folder Name'], "folder name mismatch")
        else:
            count_checks += 1
            if(row['Folder Name'] not in row['param_table'].lower()):
                str_tableMatch = row['param_table'] + " Table name and "+ row['Folder Name'] + " folder name mismatch"
                table_match_result[row['Email ID']] = str_tableMatch
                code_result = False;
                print (row['param_table'], "Table name and", row['Folder Name'], "folder name mismatch")
            else:
                table_match_result[row['Email ID']] = " "
    return table_match_result
#send email
    #for emailId in review_result_dict.keys():
def send_email(list_codeReview_result,gmail_user,gmail_pwd, emailId):  
        smtpserver = smtplib.SMTP("smtp.gmail.com", 587)
        smtpserver.ehlo()
        subject = "Automatic Code Review Result"
        smtpserver.starttls()
        smtpserver.ehlo
        smtpserver.login(gmail_user, gmail_pwd)
        TEXT = """
        
        """

        list_text = ('\n'.join(map(str, list_codeReview_result)))
        TEXT += '\n %s'% (list_text)
            
        message = 'Subject: {}\n\n{}'.format(subject, TEXT)
        #header = 'To:' + ", ".join(to) + '\n' + 'From: ' + gmail_user + '\n' + 'Subject: ' + subject + '\n'
        #body = "Following are the new companies found in boerse-frankfurt.de website." + '\n' + '   WKN  \tName' + '\n'
        #i = 0
        #for index,row in new.iterrows():
            #body += str(i + 1) + "." + row['WKN'] + "\t" + row['Name'] + "\n"
            #i += 1
        #print(body)
        #msg = header + '\n' + body + '\n\n'
        smtpserver.sendmail(gmail_user, emailId, message)
        smtpserver.close()
                                                   
           
def automatic_review(args,gmail_user,gmail_pwd):   

    path = os.path.dirname(os.path.abspath(__file__)) 

    files = os.listdir(path)    

    list_result = []
    
    isFolderNameToCheck = True
    
    
    # this is a dictionary holding Key(email ID) and Value(List of review comments)
    review_result_dict = {}

    for f in files:
        
        if(f != "jenkins") :
            
            subfolder = {}
            
            list_py = []
            list_unittest = [] 
            list_readme = []
            list_jenkins = []      


            if os.path.isdir(f):                
                path_folder = path +"/" + f
                files_folder = os.listdir(path_folder)

                for name in files_folder : 
                    #print(name)
                    if('.py' in name):
                        if( name != '__init__.py'):
                            list_py.append(name)
                    if('test' == name):
                        path_test = path_folder +"/" +name
                        files_test = os.listdir(path_test)
                        for ut in files_test : 
                            #print(ut)
                            list_unittest.append(ut)
                    if('readme' == name):
                        path_readme = path_folder +"/" +name
                        files_readme = os.listdir(path_readme)
                        for readme in files_readme : 
                            #print(ut)
                            list_readme.append(readme)
                    if('jenkins' == name):
                        path_jenkins = path_folder +"/" +name
                        files_jenkins = os.listdir(path_jenkins)
                        for ut in files_jenkins : 
                            #print(ut)
                            list_jenkins.append(ut)

                subfolder['list_py'] = list_py
                subfolder['list_readme'] = list_readme
                subfolder['list_unittest'] = list_unittest
                subfolder['list_jenkins'] = list_jenkins
                subfolder['folder_name'] = f

                list_result.append(subfolder)  
    
    df = pd.DataFrame(list_result)
    
    #print(subfolder)
    scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(args.google_key_path, scope)
    gc = gspread.authorize(credentials)
        #if(args.environment == 'pecten_production') :            
        #    wks = gc.open("subfolder_criteria_production")
        #else :
    wks = gc.open("subfolder_criteria")

    sh = wks.worksheet("Google_Forms_Input")
    df_spreadsheet = pd.DataFrame(sh.get_all_records())
    #print("printing spreadsheet dataframe")
    #print(df_spreadsheet['script_name'])
    #print(df_spreadsheet['Folder Name'])
    #print(df_spreadsheet['Email ID'])
    #print(df_spreadsheet['param_table'])
    #print(df_spreadsheet['big_query_source'])
    #print(len(df_spreadsheet))
    
    
    for index, row in df_spreadsheet.iterrows():
        if(row['Folder Name'] != ""):
            
            for subfolder in list_result : 
        #print('\n')
                if (row['Folder Name'] == subfolder['folder_name']):
                            print("Check Folder :  {} ".format(subfolder['folder_name']))
        
        
                            
                            #print(df)
                            #Check for sql table match
                            if isFolderNameToCheck:
                                isFolderNameToCheck = False
                                dict_folder_match = checkForMatch_folderName_SQLTableName(df_spreadsheet)
                                print(dict_folder_match)
                            
                            
       
                            isDuplicateHandle = False
                            isInvalidDataHandle = False
                            isParamTableMatch = False
                            isBigquerysourceMatch =False
                            isReadmeFilePresent = False
                            isJenkinFilePresent = False
                            isUnitTestFilePresent = False


                            list_codeReview_result = []
                            email_Id = row['Email ID']
                            file_py = row['script_name']
                            param_table_name = row['param_table']
                            big_query_source = row['big_query_source']
                            print(file_py)
                            print(email_Id)
                            filepath = path + '/' + subfolder['folder_name'] + '/' + file_py
                            str_title = "--Review result for the script " + file_py + " --" +'\n'
                            list_codeReview_result.append(str_title)
                            #for email in email_Id:
                            list_codeReview_result.append(dict_folder_match[email_Id])
                    
                            line_num = 1
                            hardcoded_password = []
                            hardcoded_username = []
                            hardcoded_apikey = []
                            hardcoded_BQTableName = []
                            hardcoded_email = []
                            hardcoded_url = []
                            hardcoded_date = []
                            error_logging = []
                            
                            #Check for readme
                            for file_md in subfolder['list_readme'] :
                    
                                name_file_readme = file_md.replace('.md', "")
                                name_file_readme = name_file_readme.replace('readme_', "")  
                                percent_readme = SequenceMatcher(None,file_py, name_file_readme ).ratio()
                                # #print("MD : " + str(percent_readme))

                                if(percent_readme >= 0.95000 ) :
                                    isReadmeFilePresent = True
                                    break      
                                    
                            #Check for UnitTest file
                            for file_unittest in subfolder['list_unittest'] :        
                            
                                name_file_unittest = file_unittest.replace('ut_', "")  
                                percent_unittest = SequenceMatcher(None, file_py,name_file_unittest).ratio()
                                # #print("unittest : " + str(percent_unittest))

                                if(percent_unittest >= 0.95000 ) :
                                    isUnitTestFilePresent = True
                                    break
                
                            #Check for Jenkin file
                            for file_jenkins in subfolder['list_jenkins'] :        
                            
                                name_file_jenkins = file_jenkins.replace('.py', "")
                                name_file_jenkins = name_file_jenkins.replace('Jenkinsfile', "")  
                                percent_jenkins = SequenceMatcher(None, file_py,name_file_jenkins).ratio()
                                # #print("unittest : " + str(percent_unittest))

                                if(percent_jenkins >= 0.95000 ) :
                                    isJenkinFilePresent = True
                                    break

                            with open(filepath) as fp:
                        
                                line = fp.readline()
                        
                        
                                while line:
                        
                                    # check for commented first line
                                    if((line_num == 1) and "#" not in line):
                                        list_codeReview_result.append("first line not commented")
                                
                        
                                    #check for Hardcoded Password
                                    if(re.search('password\s*=\s*(\'|\")',line, re.IGNORECASE)):
                                        print('in password')
                                        #str_pwd = "Password Hardcoded in line " + line
                                        #list_codeReview_result.append(str_pwd)
                                        hardcoded_password.append(line_num)
                                        print(line)
                
                            #check for Hardcoded Username
                                    if(re.search('username\s*=\s*(\'|\")',line, re.IGNORECASE)):
                                        print("in username")
                                        #str_User = "Username Hardcoded in line " + line
                                        #list_codeReview_result.append(str_User)
                                        hardcoded_username.append(line_num)
                                        print(line)
         
                            #check for Hardcoded APIKey
                                    if(re.search('apikey\s*=\s*(\'|\")',line, re.IGNORECASE)):
                                        print('apikey')
                                        #apikey = "apikey Hardcoded in line " + line
                                        #list_codeReview_result.append(apikey)
                                        hardcoded_apikey.append(line_num)
                                        print(line)
        
                            #check for Hardcoded Big Query table name
                                    if(re.search('bqtablename\s*=\s*(\'|\")',line, re.IGNORECASE)):
                                        print('bqtablename')
                                        #str_BQTableName = "BQ Table name Hardcoded in line " + line
                                        #list_codeReview_result.append(str_BQTableName)
                                        hardcoded_BQTableName.append(line_num)
                                        print(line)
                        
                            # check for Hardcoded email ID search
                                    if(re.search(r'[\w\.-]+@[\w\.-]+', line)):
                                        print('email')
                                        #str_email = "Email Hardcoded in line " + line
                                        #list_codeReview_result.append(str_email)
                                        hardcoded_email.append(line_num)
                                        print(line)
       
                            #check for Hardcoded URL search
                                    regex = re.compile(r'.(?:http|ftp)s?://' # http:// or https://
                                                       r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
                                                       r'localhost|' #localhost...
                                                       r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
                                                       r'(?::\d+)?' # optional port
                                                       r'(?:/?|[/?]\S+)$', re.IGNORECASE)
                                    if(re.search(regex, line) or re.search('http', line, re.IGNORECASE)):
                                        #str_url = "URL Hardcoded in line " + line
                                        #list_codeReview_result.append(str_url)
                                        hardcoded_url.append(line_num)
                                        print(line)
       
                            #check for Hardcoded date search
                                    if(re.search(r'(19[0-9][0-9])(.|-)([1-9] |1[0-2])(.|-|)([1-9] |1[0-9]| 2[0-9]|3[0-1])',line)):
                                        print('Date')
                                        #str_date = "Date Hardcoded in line " + line
                                        #list_codeReview_result.append(str_date)
                                        hardcoded_date.append(line_num)
                                        print(line)
                                        
                            #check for dedup
                                    if(re.search('handle_duplicates',line, re.IGNORECASE)):
                                        isDuplicateHandle = True;
                                        print('dedup checked')
       
                            #check for Invalid data
                                    if(re.search('handle_invalid_data',line, re.IGNORECASE)):
                                        isInvalidDataHandle = True
                                        print('invalid data checked')
        
       
                            #check for error logged to correct type
                                    if(re.search('script_type',line, re.IGNORECASE)):
                                        if not (re.search('\"script_type\"\s*:\s*\"collection\"', line, re.IGNORECASE)):
                                            error_logging.append(line_num)
                                            print(line)
                                            print('Error not logged into collection')
                                    
                             #check for ParamTable name
                                    if param_table_name in line:
                                        isParamTableMatch = True
                            
                             #check for Bigquerysource name          
                                    if  big_query_source in line:
                                        isBigquerysourceMatch =True
                                        
                                    line = fp.readline()
                                    line_num += 1
                           
                            
                    #Format the result
                            if not isDuplicateHandle:
                                code_result = False
                                list_codeReview_result.append("Duplicate data not handled")
                            if not isInvalidDataHandle:
                                code_result = False
                                list_codeReview_result.append("Invalid data not handled")
                            if not isParamTableMatch:
                                code_result = False
                                list_codeReview_result.append("Incorrect Param Table used")
                            if not isBigquerysourceMatch:
                                code_result = False
                                list_codeReview_result.append("Incorrect Big query source used")
                            if not isReadmeFilePresent:
                                code_result = False
                                list_codeReview_result.append("ReadMe file not present")
                            if not isJenkinFilePresent:
                                code_result = False
                                list_codeReview_result.append("Jenkins file not present")
                            if not isUnitTestFilePresent:
                                code_result = False
                                list_codeReview_result.append("UnitTest file not present")
                            if (len(hardcoded_password) != 0):
                                code_result = False
                                str_pwd = "Password Hardcoded in lines: " + '\n' + (str(hardcoded_password).strip('[]'))+ '\n' + 'Count:'+ str(len(hardcoded_password)) +'\n'
                                list_codeReview_result.append('\n' + str_pwd)
                            if (len(hardcoded_username) != 0):
                                code_result = False
                                str_username = "Username Hardcoded in lines: " + '\n' + (str(hardcoded_username).strip('[]'))+ '\n' + 'Count:'+ str(len(hardcoded_username))
                                list_codeReview_result.append('\n' + str_username)
                            if (len(hardcoded_apikey) != 0):
                                code_result = False
                                str_apikey = "API Key Hardcoded in lines: " + '\n' + (str(hardcoded_apikey).strip('[]'))+ '\n' + 'Count:'+ str(len(hardcoded_apikey))
                                list_codeReview_result.append('\n' + str_apikey)
                            if (len(hardcoded_BQTableName) != 0):
                                code_result = False
                                str_BQTable = "BQ Table name Hardcoded in lines: " + '\n' + (str(hardcoded_BQTableName).strip('[]'))+ '\n' + 'Count:'+ str(len(hardcoded_BQTableName))
                                list_codeReview_result.append('\n' + str_BQTable)
                            if (len(hardcoded_email) != 0):
                                code_result = False
                                str_email = "Email ID Hardcoded in lines: " + '\n' + (str(hardcoded_email).strip('[]'))+ '\n' + 'Count:'+ str(len(hardcoded_email))
                                list_codeReview_result.append('\n' + str_email)
                            if (len(hardcoded_url) != 0):
                                code_result = False
                                str_url = "URL Hardcoded in lines: " + '\n' + (str(hardcoded_url).strip('[]'))+ '\n' + 'Count:'+ str(len(hardcoded_url))
                                list_codeReview_result.append('\n' + str_url)
                            if (len(hardcoded_date) != 0):
                                code_result = False
                                str_date = "Date Hardcoded in lines: " + '\n' + (str(hardcoded_date).strip('[]'))+ '\n' + 'Count:'+ str(len(hardcoded_date))
                                list_codeReview_result.append('\n' + str_date)
                            if (len(error_logging) != 0):
                                code_result = False
                                str_error_log_dest = "Errors not logged into collection universe in lines: " + '\n' + (str(error_logging).strip('[]'))+ '\n' + 'Count:'+ str(len(error_logging))
                                list_codeReview_result.append('\n' + str_error_log_dest)
                    
                            #send email
                            send_email(list_codeReview_result, gmail_user, gmail_pwd, email_Id)
                            
                            #for emails in email_Id:
                                #review_result_dict[emails]= list_codeReview_result
                            
                    # with open(path + '/' + subfolder['folder_name'] + '/' + file_py, "r", encoding='UTF8') as f:
                        # for line in f.readlines():
                            # param_table1 = "\""+  list_excel_df[1]+ "\""
                            # param_table2 = "\'"+  list_excel_df[1]+ "\'"
                            # if param_table1 in line:
                                        # dict_files['param_table'] = ""
                            # elif param_table2 in line:
                                        # dict_files['param_table'] = ""

                            # bigquery1 = "\""+  list_excel_df[0]+ "\""
                            # bigquery2 = "\'"+  list_excel_df[0]+ "\'"
                            # if  bigquery1 in line:
                                        # dict_files['big_query_source'] = ""
                            # elif bigquery2 in line:
                                        # dict_files['big_query_source'] = ""
                            
                        
        
        
            #for key in review_result_dict.keys() & dict_folder_match.keys():
                #review_result_dict[key].append("Folder name and SQL table name mistmatch list")
                #review_result_dict[key].append(dict_folder_match[key])
                                                   

        
        # list_subfolder_correct_file.append(dict_files)

        #print(list_files_result)         

        # df1 = pd.DataFrame(list_subfolder_correct_file)
        # df2 = pd.DataFrame(list_subfolder_not_specified_file)

        #print('\n')
        # print(" Folder :  {} / Correct ".format(subfolder['folder_name']))
        # print('\n')
        # print(df1)

        #print('\n')
        #print(" Folder :  {} / Incorrect".format(subfolder['folder_name']))
        #print('\n')
        #print(df2)

        # if(args.environment == 'pecten_production') :            
            # sh = gc.open("pecten_collection_subfolder_results_production")
        # else :
            # sh = gc.open("pecten_collection_subfolder_results")
        

        # worksheet = sh.worksheet(subfolder['folder_name'])

        # size_df1 = len(df1)
        # column_df1 = len(df1.columns)
        
        # stringList = ["A3:A", "B3:B", "C3:C", "D3:D", "E3:E", "F3:F", "G3:G", "H3:H", "I3:I", "J3:J", "K3:K", "L3:L", "M3:M", "N3:N", "O3:O", "P3:P", "Q3:Q", "R3:R", "S3:S", "T3:T", "U3:U", "V3:V", "W3:W", "X3:X", "Y3:Y", "Z3:Z"]
    
        # if(size_df1 != 0):

            # stringList_df1 = stringList[0:column_df1]

            # #for j in range(column_df1):
                # #worksheet.update_cell(2, j+1, df1.columns.values[j])    

            # row_df1 = size_df1 + 2

            # for i in range(column_df1):

                # myString = stringList_df1[i] + str(row_df1)
                # cell_list = worksheet.range(myString)
                # #print(len(cell_list))

                # for x in range(len(cell_list)):
                    # cell_list[x].value = df1.iloc[x-1, i]

        
                # # Update in batch
                # #worksheet.update_cells(cell_list)

        # size_df2 = len(df2)
        # #column_df2 = len(df2.columns)

        # if(size_df2 != 0):

            # string_df2 = stringList[9]          
            
            # #worksheet.update_cell(2, 10, df2.columns.values[5])    
            
            # row_df2 = size_df2 + 2
                
            # #print(stringList_df2[i])
            # myString = string_df2 + str(row_df2)
            # #print(myString)
            # cell_list = worksheet.range(myString)
            # #print(len(cell_list))

            # for x in range(len(cell_list)):                    
                # cell_list[x].value = df2.iloc[x-1, 5]       

            # # Update in batch
           # # worksheet.update_cells(cell_list)
    
    
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    args.python_path = os.environ.get('PYTHON_PATH', '')
    args.google_key_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')
    args.environment = os.environ.get('ENVIRONMENT', '')
    args.param_connection_string = os.environ.get('MYSQL_CONNECTION_STRING', '')
    args.bucket_name = os.environ.get("BUCKET_NAME", 'pecten-duplication')
    args.duplicates_log_table = os.environ.get("DUPLICATES_LOG_TABLE", 'duplicate_data_utils')
    args.invalid_log_table = os.environ.get("INVALID_LOG_TABLE", "invalid_data_utils")
    sys.path.insert(0, args.python_path)
    main(args)