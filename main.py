from fogbugz import FogBugz
from s import getpath, getcolumns, getapikeyassistant, yes
from datetime import datetime
import time

CONST_DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
FORMAT_OF_DATE = '%Y-%m-%d %H:%M:%S'
CQA_GRABBAG_ID = 657

class FogbugzCase:
    def __init__(self, ixBug, sTitle, sPersonAssignedTo, sStatus, dtLastUpdated, Tester, ixBugParent, sCategory):
        self.ixBug = ixBug
        self.sTitle = sTitle
        self.sPersonAssignedTo = sPersonAssignedTo
        self.sStatus = sStatus
        self.dtLastUpdated = dtLastUpdated
        self.Tester = Tester
        self.ixBugParent = ixBugParent
        self.sCategory = sCategory


def getcaseslist(fb, query):
    print("Started gathering data...")
    start = time.time()
    resultXML = fb.search(q=query, cols=getcolumns())
    end = time.time()
    print('Finished gathering data. Time spent: ' + str(end-start))

    resultxmllist = list(resultXML.cases.childGenerator())
    resultlistofcases = list()
    for c in resultxmllist:
        caseObject = FogbugzCase(c.ixBug.string, c.sTitle.string, c.sPersonAssignedTo.string, c.sStatus.string,
        datetime.strptime(c.dtLastUpdated.string, CONST_DATE_FORMAT), c.Tester.string, c.ixBugParent.string, c.sCategory.string)
        resultlistofcases.append(caseObject)

    resultlistofcases.sort(key=lambda r: r.ixBug)

    return resultlistofcases


def particularcaseevents(fb, case):
    respBug = fb.search(q=str(case), cols='sTitle,sPersonAssignedTo,sStatus,events')
    xmlBug = respBug.cases.findAll('case')[0]
    bug = parseCase(xmlBug)
    return bug


def parseCase(xmlBug):
    bug = {}
    bug['ixBug'] = int(xmlBug['ixBug'])
    bug['sTitle'] = xmlBug.sTitle.string if xmlBug.sTitle.string else ''
    bug['sPersonAssignedTo'] = xmlBug.sPersonAssignedTo.string if xmlBug.sPersonAssignedTo.string else ''
    bug['sStatus'] = xmlBug.sStatus.string if xmlBug.sStatus.string else ''
    bug['events'] = []
    for event in xmlBug.events.findAll('event'):
        bugEvent = {}
        bugEvent['ixBugEvent'] = int(event['ixBugEvent'])
        bugEvent['sVerb'] = event.sVerb.string if event.sVerb.string else ''
        bugEvent['dt'] = datetime.strptime(event.dt.string, CONST_DATE_FORMAT) if event.dt.string else ''
        bugEvent['s'] = event.s.string if event.s.string else ''
        bugEvent['sChanges'] = event.sChanges.string if event.sChanges.string else ''
        bugEvent['evtDescription'] = event.evtDescription.string if event.evtDescription.string else ''
        bugEvent['sPerson'] = event.sPerson.string if event.sPerson.string else ''
        bug['events'].append(bugEvent)
    return bug


def getparticularcase(fb, caseid):
    resultxml = fb.search(q=caseid, cols=getcolumns())
    for case in resultxml.cases.childGenerator():
        return case


def findinguserbyevents(case):
    fb = FogBugz(getpath(), getapikeyassistant(), api_version=8)
    bugevents = particularcaseevents(fb, case)

    for event in bugevents['events']:
        s = event['sChanges']

        # Looking for "Status changed from 'xxxxx' to 'Active'
        statuslines = [sentence for sentence in s.split('\r\n') if 'Status changed' in sentence]
        if statuslines:
            fromtostring = statuslines[0].split('\'')
            if fromtostring[3] == 'Active':
                if str(event['sPerson']) is not None:
                    # print(str(bugevents['ixBug']) + " " + str(event['sPerson']) + " " + "From " + fromtostring[1] + " to " + fromtostring[3])
                    return str(event['sPerson'])

        # If there is no status change, let's say a case was Active already, because reported internally
        # Looking for "Category changed from 'xxxxx' to 'Unity'
        statuslines = [sentence for sentence in s.split('\r\n') if 'Project changed' in sentence]
        if statuslines:
            fromtostring = statuslines[0].split('\'')
            if fromtostring[3] == 'Unity':
                if str(event['sPerson']) is not None:
                    # print(str(bugevents['ixBug']) + " " + str(event['sPerson']) + " " + "From " + fromtostring[1] + " to " + fromtostring[3])
                    return str(event['sPerson'])


def findowner(fb, cases):
    for c in cases:
        # If it's not a backport and tester field is set
        if c.sCategory != "Backport" and c.Tester != "0":
            # Find person's name by id
            person = findpersonbyid(fb, c.Tester)
            # If a person is still working here
            if person != "Null":
                print("1 Tester is not null giving " + c.ixBug + " to " + person)
                editcase(fb, c.ixBug, c.Tester, "")
            # If not
            else:
                print("2 Tester is null, assigning to CQA")
                editcase(fb, c.ixBug, CQA_GRABBAG_ID, "Couldn't find a tester. #cqa-bots")

        # If it's not a backport and tester is not set
        if c.sCategory != "Backport" and c.Tester == "0":
            # Find owner's name by events
            name = findinguserbyevents(str(c.ixBug))
            # Find out if the person is still working
            person = findpersonbyname(fb, name)
            # If a person is working
            if person != "Null":
                print("3 Tester is not Null events giving " + c.ixBug + " to " + name + " id " + person)
                editcase(fb, c.ixBug, person, "Tester field was not set. If you are a developer, assign this case to your internal QA for the verification. If you are not an owner of this case, assign it to Customer QA Grabbag. Otherwise, please verify. :) #cqa-bots")
            # If a person is not working anymore
            else:
                print("4 Tester is Null, giving " + c.ixBug + " to CQA")
                editcase(fb, c.ixBug, CQA_GRABBAG_ID, "Couldn't find a tester. #cqa-bots")

        # If it's a backport
        if c.sCategory == "Backport":
            # Find main case
            tempcase = getparticularcase(fb, c.ixBugParent)
            # Is there a tester on the main case?
            if tempcase.Tester.string != "0":
                person = findpersonbyid(fb, tempcase.Tester.string)
                # If a person is still working here
                if person != "Null":
                    print("5 Tester is not null giving " + c.ixBug + " to " + person)
                    editcase(fb, c.ixBug, tempcase.Tester.string, "")
                # If not
                else:
                    print("6 Tester is Null, giving " + c.ixBug + " to CQA")
                    editcase(fb, c.ixBug, CQA_GRABBAG_ID, "Couldn't find a tester. #cqa-bots")
            # If there is no tester on the main case
            else:
                # Find owner's name by events
                name = findinguserbyevents(str(tempcase.ixBug.string))
                # Find out if the person is still working
                person = findpersonbyname(fb, name)
                # If a person is working
                if person != "Null":
                    print("7 Tester is not Null events giving " + c.ixBug + " to " + name)
                    editcase(fb, c.ixBug, person, "Tester field was not set. If you are a developer, assign this case to your internal QA for the verification. If you are not an owner of this case, assign it to Customer QA Grabbag. Otherwise, please verify. :) #cqa-bots")
                # If a person is not working anymore
                else:
                    print("8 Tester is Null, giving " + c.ixBug + " to CQA")
                    editcase(fb, c.ixBug, CQA_GRABBAG_ID, "Couldn't find a tester. #cqa-bots")


def editcase(fb, id, assigntoid, message):
    resp = fb.edit(ixBug=id, ixPersonAssignedTo=assigntoid, sEvent=message)


def findpersonbyid(fb, personsid):
    people = fb.listPeople()
    for p in people.findAll('person'):
        if p.ixPerson.string == personsid:
            return p.sFullName.string

    return "Null"


def findpersonbyname(fb, personsname):
    people = fb.listPeople()
    for p in people.findAll('person'):
        if p.sFullName.string == personsname:
            return p.ixPerson.string

    return "Null"


def main():
    # Program start and timer
    print("Started the program... ")
    print(str(datetime.now().strftime(FORMAT_OF_DATE)))
    start = time.time()

    # Fogbugz init
    fb = FogBugz(getpath(), getapikeyassistant(), api_version=8)
    bugcases = getcaseslist(fb, query=yes())
    findowner(fb, bugcases)

    # Finish time
    end = time.time()
    print('Finished program. Time spent: ' + str(end-start))
    print(str(datetime.now().strftime(FORMAT_OF_DATE)))

sleeptime = 1780

while True:
    try:
        main()
    except:
        print(str(datetime.now().strftime(FORMAT_OF_DATE)))
        print("Fogbugz not working or internet down")
    print("Sleeping for 30 minutes")
    time.sleep(sleeptime)

