"""
py 2.7
generate delimted file of attendance records from a list of course_ids
developed by jeff.kelley@blackboard.com  July 2019

BLACKBOARD MAKES NO REPRESENTATIONS OR WARRANTIES ABOUT THE SUITABILITY
OF THE SOFTWARE, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE, OR NON-INFRINGEMENT. BLACKBOARD SHALL NOT BE LIABLE FOR ANY
DAMAGES SUFFERED BY LICENSEE AS A RESULT OF USING, MODIFYING OR
DISTRIBUTING THIS SOFTWARE OR ITS DERIVATIVES.

logic..
Authenticate to get token
Itterate through the list of cousres:
 - Create a list/dictionary of user attributes for all the members of the course
 - Get all the course meetings in a library
   - for each meeting, get the attendance records for all members
     - add the user attributes for each person
     - output the records with attendance and user values

TODO:


Validate inputs
 - Course IDs  no spaces
 - KEY  length, no spaces
 - SECRET   length, no spaces
 - HOST  format?, no spaces
 - RESULTLIMIT  number between 1 and 100 

"""

import requests
import json
import datetime
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import ssl
import sys
import csv
import argparse
import ConfigParser


#########
class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("logfile.log", "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
        pass    

#### 
#parse and ready the arguments from the command line 
parser = argparse.ArgumentParser(description='Properties, Input file and Output file')
parser.add_argument("PROPERTIES_FILE", help="The properties file")
parser.add_argument("INPUT_FILE", help="List of Learn Course IDs")
parser.add_argument("OUTPUT_FILE", help="CSV with attendance records")

args = parser.parse_args()
propFile = args.PROPERTIES_FILE
inFile = args.INPUT_FILE
outFile = args.OUTPUT_FILE

# read the properties file into "config" container
config = ConfigParser.SafeConfigParser()
config.read(propFile)

# setting and validating variables from properties file
KEY = config.get('properties', 'KEY')
SECRET = config.get('properties', 'SECRET')
HOST = config.get('properties', 'HOST')
RESULTLIMIT = config.get('properties', 'RESULTLIMIT')

if (' ' in [KEY, SECRET, HOST, RESULTLIMIT]) \
  or (len(SECRET) < 32) \
  or (RESULTLIMIT < 1 or RESULTLIMIT > 100)\
  or ('https' not in HOST):
    print('[' + str(datetime.datetime.now()) + ']| Property value failed validataion. Check ' + propFile)
    sys.exit()


#########################
class doAuthenticate:
  #reads the constants HOST, KEY, SECRET to get token and related attributes
  def __init__(self):
    
    AUTHDATA = {
      'grant_type': 'client_credentials'
    }

    r = requests.post(HOST + '/learn/api/public/v1/oauth2/token', data=AUTHDATA, auth=(KEY, SECRET))
    if r.status_code == 200:  #success
      parsed_json = json.loads(r.text)  #read the response into dictionary
      self.token = parsed_json['access_token'] 
      self.expiresIn = parsed_json['expires_in']
      m, s = divmod(self.expiresIn, 60)  #convert token lifespan into m minutes and s seconds
      self.expiresAt = datetime.datetime.now() + datetime.timedelta(seconds = s, minutes = m) 
      self.authStr = 'Bearer ' + self.token
      print('[' + str(datetime.datetime.now()) + ']|Token ' + self.token + ' Expires in ' + str(m) + ' minutes and '+ str(s) + ' seconds. (' + str(self.expiresAt) + ')' )
    else:  #failed to authenticate
      print ('Failed to authenticate: ' + r)
      sys.exit()

##################
class nearlyExpired:
  #pauses and reauthenticates if expriation within x seconds
  def __init__(self,sessionExpireTime):
      bufferSeconds = 120
      self.expired = False
      self.time_left = (sessionExpireTime - datetime.datetime.now()).total_seconds()
      #self.time_left = 30  #use for testing
      if self.time_left < bufferSeconds:
            print ('[' + str(datetime.datetime.now()) + ']|PLEASE WAIT  Token almost expired retrieving new token in ' + str(bufferSeconds) + 'seconds.')
            time.sleep(bufferSeconds + 1)
            self.expired = True


#########################
# Dev documentation missing note for membership endpoint: 
# to get user.externalId integration user needs privilge [entitlement]
# Administrator Panel (Users) > Users   [system.user.VIEW]
#
class getMembers:
  #input a course_id get list of nested dictionaries with user attributes for enrolled users
  def __init__(self, course_Id):
    self.thisId = course_Id
    # print ('Getting membership information for ' + self.thisId)
    ROOTCOURSEURL = '/learn/api/public/v1/courses/courseId:' + self.thisId
    GETMEMURL = ROOTCOURSEURL + '/users?expand=user&fields=user.id,user.externalId,user.userName,user.studentId&limit=' + str(RESULTLIMIT)
    MEMBERS = [] ## initialize list
    while len(GETMEMURL) > 0 :  ## account for paging
      #print (GETMEMURL)
      getMembers = requests.get(HOST + GETMEMURL, headers={'Authorization':thisAuth.authStr})
      #print(getMembers)
      if getMembers.status_code != 200:
        print ('Error getting members for course: ' + self.thisId)
        print ('Status: ' + str(getMembers.status_code))
        break #get out this while loop
      members = json.loads(getMembers.text)
      #print (members)
      MEMBERS = MEMBERS + members["results"]
      if 'paging' in members:  # there are more members
        GETMEMURL = members["paging"]["nextPage"]
      else:  # there are no more members
        GETMEMURL = ''
    self.members = MEMBERS

######################
class getMeetings:
  #input a course ID and get a list of meetings
  def __init__(self, course_Id):
    self.thisId = course_Id
    # print ('Getting meeting information for ' + self.thisId)
    ROOTCOURSEURL = '/learn/api/public/v1/courses/courseId:' + self.thisId
    GETMEETINGSURL = ROOTCOURSEURL + '/meetings?limit=' + str(RESULTLIMIT)
    MEETINGS = []  # initialize list
    while len(GETMEETINGSURL) > 0 : ## account for paging
      #print (GETMEETINGSURL)
      getMeetings = requests.get(HOST + GETMEETINGSURL, headers={'Authorization':thisAuth.authStr})
      #print(getMeetings)          
      if getMeetings.status_code != 200:
        print('Error getting meetings for course: ' + self.thisId)
        break #get out of this while loop
      meetings = json.loads(getMeetings.text)
      #print (meetings)
      MEETINGS = MEETINGS + meetings["results"]
      if 'paging' in meetings:
          GETMEETINGSURL = meetings["paging"]["nextPage"]
      else:  #there are no more meetings
          GETMEETINGSURL = ''
    self.meetings = MEETINGS


#############################
## There is a bug in GET /learn/api/public/v1/courses/{courseId}/meetings/{meetingId}/users
## only the primary course ID value is acceptable   eg  _2221_1
class getRecords:
  #input a meeting ID and coursePK >> get an attendance records list
  def __init__ (self, meeting_Id, courseId):
    self.thisCourse = courseId
    self.thisMeeting = meeting_Id
    # print('Getting attendance for meeting ' + self.thisMeeting + ' course ' + self.thisCourse)
    GETRECORDSURL = '/learn/api/public/v1/courses/' + self.thisCourse + '/meetings/' + self.thisMeeting + '/users?limit=' + str(RESULTLIMIT)
    RECORDS = []  #initialize list
    while len(GETRECORDSURL) > 0 : #account for paging
      #print (GETRECORDSURL)
      getRecords = requests.get(HOST + GETRECORDSURL, headers={'Authorization':thisAuth.authStr})
      if getRecords.status_code != 200:
        print('problem getting records')
        break
      records = json.loads(getRecords.text)
      #print (records)
      RECORDS = RECORDS + records["results"]
      if 'paging' in records:
        GETRECORDSURL = records["paging"]["nextPage"]
      else:  #there are no more records
        GETRECORDSURL = ''
    self.records = RECORDS 


#################################
## START THE SCRIPT ###

sys.stdout = Logger()
batchStart = datetime.datetime.now()
batchId = batchStart.strftime("%Y%m%d-%H%M")
print ('[' + str(batchStart) + ']|Starting Batch Attendance ID = ' + batchId)

thisAuth = doAuthenticate()


#file readiness
inputFile = open(inFile)
outputFile = open(outFile, 'wb')
outputWriter = csv.writer(outputFile, delimiter='|')
# this is the output file header
header = ['COURSE_ID','COURSE_PK1', 'MEETING_ID', 'MEETING_START', 'MEETING_END', 'STATUS', 'USER_PK1', 'USERNAME', 'EXTERNAL_USER_KEY','STUDENT_ID']
outputWriter.writerow(header)
rowCounter = 0



## itterate over the ids in the input file
for line in inputFile:
    if nearlyExpired(thisAuth.expiresAt).expired:
        thisAuth = doAuthenticate()
    
    thisId = line.rstrip()
    #print ('[' + str(datetime.datetime.now()) + ']|'+ thisId + '|Start this course')

    thisMeetings = getMeetings(thisId)
    meetingCount = len(thisMeetings.meetings)
    if meetingCount == 0: 
        print('[' + str(datetime.datetime.now()) + ']|'+ thisId + '|No meetings.')
        continue

    thisMembers = getMembers(thisId)
    memberCount = len(thisMembers.members)
    if memberCount == 0: 
        print('[' + str(datetime.datetime.now()) + ']|'+ thisId + '|No members.')
        continue

    thisMeetings = getMeetings(thisId)
    meetingCount = len(thisMeetings.meetings)
    if meetingCount == 0: 
        print('[' + str(datetime.datetime.now()) + ']|'+ thisId + '|No meetings.')
        continue

    allRecords = []  # initialize list
    for meeting in thisMeetings.meetings:
        thisRecords = getRecords(str(meeting['id']), meeting['courseId'])
        allRecords = thisRecords.records + allRecords
    recordCount = len(allRecords)
    if recordCount == 0: 
        print('[' + str(datetime.datetime.now()) + ']|'+ thisId + '|No attendance records.')
        continue

    print('[' + str(datetime.datetime.now()) + ']|'+ thisId + '|' + str(memberCount) + ' members, ' + str(meetingCount) + ' meetings, and ' + str(recordCount) + ' attendance records.')

    # combine data and write to outFile
    for rec in allRecords:
        mtg = next((meet for meet in thisMeetings.meetings if str(meet['id']) == str(rec['meetingId'])), None)
        usr = next((mem['user'] for mem in thisMembers.members if mem['user']['id'] == rec['userId']), None)
        if usr == None:  #condition where user id found in records doesn't exist in memberships. User or membership deleted.
            print('[' + str(datetime.datetime.now()) + ']|'+ thisId + '|Attendance Record for unenrolled/deleted user: '+ rec['userId'])
            continue
        attendanceRow = [thisId, mtg['courseId'], str(mtg['id']),\
            mtg['start'], mtg['end'], rec['status'], rec['userId'],\
            usr['userName'], usr['externalId'], usr.get('studentId')]
            # notice we use usr.get('studentId') to accomodate records without a studentId value
        outputWriter.writerow(attendanceRow)
        rowCounter = rowCounter + 1

# lets close up shop
outputFile.close()
inputFile.close()
print ('[' + str(datetime.datetime.now()) + ']|Closing batch ' + batchId + ' with ' + str(rowCounter) + ' records.')
