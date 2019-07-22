from fogbugz import FogBugz
from s import getpath, getcolumns, getapikey, getallfixedbugs, yes
from datetime import datetime
import time

CONST_DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
FORMAT_OF_DATE = '%Y-%m-%d %H:%M:%S'

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
        print(c)
        caseObject = FogbugzCase(c.ixBug.string, c.sTitle.string, c.sPersonAssignedTo.string, c.sStatus.string,
        datetime.strptime(c.dtLastUpdated.string, CONST_DATE_FORMAT), c.Tester.string, c.ixBugParent.string, c.sCategory.string)
        resultlistofcases.append(caseObject)

    resultlistofcases.sort(key=lambda r: r.ixBug)

    return resultlistofcases


def particlarcaseevents(fb, case):
    resultXML = fb.search(q=str(case), cols=getcolumns())

    resultxmllist = list(resultXML.cases.childGenerator())
    resultlistofcases = list()
    bugevents = list()

    print("Looking for " + str(case) + " events")
    respBug = fb.search(q=str(case),
                        cols='sTitle,sPersonAssignedTo,sStatus,events')
    xmlBug = respBug.cases.findAll('case')[0]
    bug = parseCase(xmlBug)
    bugevents.append(bug)

    resultlistofcases.sort(key=lambda r: r.ixBug)

    return resultlistofcases, bugevents


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
        bugEvent['s'] = event.s.string if event.s.string else ''
        bug['events'].append(bugEvent)
    return bug


def getparticularcase(fb, caseid):
    resultxml = fb.search(q=caseid, cols=getcolumns())
    for case in resultxml.cases.childGenerator():
        print(case)
        return case


def findinguserbyevents(case):
    fb = FogBugz(getpath(), getapikey(), api_version=8)
    cases, bugevents = particlarcaseevents(fb, case)

    for i in range(len(bugevents)):
        for event in bugevents[i]['events']:
            s = event['sChanges']

            statuslines = [sentence for sentence in s.split('\r\n') if 'Status' in sentence]
            if statuslines:
                fromtostring = statuslines[0].split('\'')
                if fromtostring[3] == 'Active':
                    print(str(bugevents[i]['ixBug']) + " " + str(event['sPerson']) + " " + "From " + fromtostring[1] + " to " + fromtostring[3])


def findowner(fb, cases):
    for c in cases:
        if c.sCategory != "Backport" and c.Tester != "0":
            print("giving " + c.ixBug + " to " + findperson(fb, c.Tester))
        if c.sCategory == "Backport":
            tempcase = getparticularcase(fb, c.ixBugParent)
            if tempcase.Tester != "0":
                print("giving " + c.ixBug + " to " + findperson(fb, tempcase.Tester.string))


def findperson(fb, personsid):
    people = fb.listPeople()
    for p in people.findAll('person'):
        if p.ixPerson.string == personsid:
            return p.sFullName.string


def main():
    # Program start and timer
    print("Started the program... ")
    print(str(datetime.now().strftime(FORMAT_OF_DATE)))
    start = time.time()

    # Fogbugz init
    fb = FogBugz(getpath(), getapikey(), api_version=8)
    bugcases = getcaseslist(fb, query=getallfixedbugs())
    findowner(fb, bugcases)

    # Finish time
    end = time.time()
    print('Finished program. Time spent: ' + str(end-start))
    print(str(datetime.now().strftime(FORMAT_OF_DATE)))



main()



