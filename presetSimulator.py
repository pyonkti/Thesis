# -*- coding: utf-8 -*-
"""
Created on Fri May 15 23:59:39 2020

@author: Billy
"""
import fastTeamLapTimeGenerator as hamLTG
import overtake as otkCalculator
import overlap as olpCalculator
import pandas as pd
import re
from datetime import datetime


lapTime = pd.read_csv("./learn/lap_times.csv")
driverInfo = pd.read_csv("./learn/drivers.csv")
driverInfo= driverInfo.drop(columns= ['driverRef','number','forename','surname','dob','nationality','url'], axis=1)
tyreChoice = pd.read_csv("./learn/tyre.csv")
merged = driverInfo.merge(lapTime, left_on='driverId', right_on = 'driverId', how = 'right')
merged = merged.drop(columns= ['driverId'], axis=1)
pd.set_option('display.max_columns',None)
pd.set_option('display.width', 1000)    
positionGlobal = list()
timeCostGlobal = list()
gapGlobal= list()
overtakeGlobal = list()
beOvertakenGlobal = list()

class Race(object):
    raceId = 0                                                                  # the ID that tell what race it is
    codes = tuple()                                                             # Tuple used for initiating other dictionaries
    lastPitLap = tuple()                                                        # Tuple created for initiatng variables
    pitTimes = dict()                                                           # How many times the racer had pitted
    lastLap = tuple()                                                           # Stores last lap number
    currentTime = 0                                                             # Stores current time by accumulting
    renewOrder = 0                                                              # Predicted location for the next lap
    dropRacer = list()                                                          # Racers that will not be racing in the next lap
    fastDrivers = list()                                                        # Operable and modeled six racers 
    timeCosts = dict()                                                          # Time counter from the start to the next lap
    lap = dict()                                                                # Current lap 
    lastPit = dict()                                                            # Stores the lap where the last pit happens
    driverNextLapTime = dict() 
    driverLastLapTime = dict()
    pitLaneTime = dict()
    vscStart = list()
    vscLast = list()
    vscTimes = 0
    raceData = 0                                                                # Specific race data for one mathch
    overtakeCount = 0
    beOvertakenCount = 0
    player = ''
    endFlag = False                                                             # Whether user called for quit or not
    pauseFlag = False                                                           # Whether user called pause or not
    raceEndFlag = False                                                         # Wheter the race is ended or not
    finalResultFlag = False
    dropFlag = False
    sortFlag = False
    vscFlag = False      
    lateInstructionFlag = False                                                 # Whether too late for giving instruction at this lap or not

    """
    The output result for every update
    """
    result = pd.DataFrame(columns=('code', 'raceId', 'lap', 'position', 'time', 'milliseconds','totalTimeCost','timeGap','selfComparison','tyreCondition')) 
    
    def __init__(self, raceId, choosenDriver):
        
        """
        class variables initiation
        """
        self.player = choosenDriver
        self.raceId = raceId
        self.raceData = merged[merged['raceId'].isin([self.raceId])] 
        self.raceData = self.raceData.reset_index(drop=True)
        self.codes = tuple(set(self.raceData['code']))
        self.lastPitLap = (0,)*len(self.codes)
        self.timeCosts = dict(zip(self.codes,self.lastPitLap))
        self.lastLap = (1,)*len(self.codes)
        self.lap = dict(zip(self.codes,self.lastLap))
        self.lastPit = dict(zip(self.codes,self.lastPitLap))
        self.pitTimes = dict(zip(self.codes,self.lastPitLap))
        self.driverLastLapTime = dict(zip(self.codes,self.lastPitLap))
        self.driverNextLapTime = dict(zip(self.codes,self.lastPitLap))
        self.pitLaneTime = dict(zip(self.codes,self.lastPitLap))
        self.vscStart = [86400]
        self.vscLast = [65000]
        self.vscTimes = 0
        self.overtakeCount = 0
        self.beOvertakenCount = 0
        self.fastDrivers = ["HAM","BOT","LEC","VET","VER","GAS"]
        self.result.drop(self.result.index,inplace=True) 
        self.dropRacer = list()
        self.endFlag = False                                                             # Whether user called for quit or not
        self.pauseFlag = False                                                           # Whether user called pause or not
        self.raceEndFlag = False                                                         # Wheter the race is ended or not
        self.finalResultFlag = False
        self.dropFlag = False
        self.sortFlag = False    
        self.lateInstructionFlag = False
        self.vscFlag = False
        """
        Preload first lap statistics before started
        """
        
        firstLap = self.raceData[self.raceData['lap'].isin([1])]
        firstLap = firstLap.reset_index(drop=True)
        for i,v in enumerate(set(firstLap['code'])):
            if firstLap['code'][i] in self.fastDrivers:
                if firstLap['code'][i] == "GAS":
                    currentLapTime = int(hamLTG.startOff(int(hamLTG.lapTimeUsedSoft(2,firstLap['code'][i])),firstLap['code'][i]))
                else:
                    currentLapTime = int(hamLTG.startOff(int(hamLTG.lapTimeUsedMedium(2,firstLap['code'][i])),firstLap['code'][i]))
                self.timeCosts[firstLap['code'][i]] = currentLapTime
                self.driverLastLapTime[firstLap['code'][i]] = currentLapTime
                self.driverNextLapTime[firstLap['code'][i]] = currentLapTime
                self.raceData.loc[(self.raceData['code']== firstLap['code'][i]) & (self.raceData['raceId']==self.raceId) & (self.raceData['lap']==self.lap[firstLap['code'][i]]), 'milliseconds'] =  currentLapTime
                continue
            for key,value in self.timeCosts.items():
                if key == firstLap['code'][i]:
                    currentLapTime = firstLap.iloc[i,5]
                    self.timeCosts[key] = currentLapTime
                    self.driverLastLapTime[key] = currentLapTime  
        self.timeCosts = dict(sorted(self.timeCosts.items(), key=lambda x: x[1]))
        self.fun_timer()
        
    def output(self,racerInput,key):
        temp = {col: racerInput[col].tolist() for col in racerInput.columns}
        for tempKey, value in temp.items():
            temp[tempKey] = str(temp[tempKey]).strip('[]').strip('\'')
        temp['totalTimeCost'] = self.timeCosts[key]
        temp['timeGap'] = ''
        self.renewOrder = self.findPosition(temp)
        emptyFlag = True
        for i, resultKey in enumerate(self.result['code'].tolist()):
            if key == resultKey:
                emptyFlag = False
                negativeFlag = False
                selfTimeStamp = int(temp['milliseconds'])-self.driverLastLapTime[key]
                self.driverLastLapTime[key] = int(temp['milliseconds'])
                selfTimeStamp /= 1000
                if selfTimeStamp < 0:
                    selfTimeStamp = -selfTimeStamp
                    negativeFlag = True               
                timearr = datetime.fromtimestamp(selfTimeStamp)
                otherStyleTime = datetime.strftime(timearr,"%M:%S.%f")[:-3]
                if negativeFlag:
                    temp['selfComparison']='\033[32m'+'-'+ otherStyleTime  +'\033[0m'
                else:
                    temp['selfComparison']='\033[31m'+'+'+ otherStyleTime  +'\033[0m'
                temp['time'] = str(self.timeTransformer(int(temp['milliseconds'])))
                self.result = self.result[self.result.code != key]
                df1 = self.result.loc[:self.renewOrder-1]
                df2 = self.result.loc[self.renewOrder:]
                df3 = pd.DataFrame([temp])
                df3['tyreCondition'] = self.tyreCondition(df3)
                self.result = df1.append(df3, ignore_index = True).append(df2, ignore_index = True)
        if emptyFlag:
            temp['tyreCondition'] = self.tyreCondition(pd.DataFrame([temp])) 
            temp['selfComparison'] = '+00.00'
            timeStamp = int(temp['milliseconds'])
            timeStamp /= 1000
            timearr = datetime.fromtimestamp(timeStamp)
            otherStyleTime = datetime.strftime(timearr,"%M:%S.%f")[:-3]
            outputTime = str(otherStyleTime)
            temp['time'] = outputTime
            self.result.loc[self.renewOrder] = temp
        gapTimeStamp = int(temp['totalTimeCost']) - int(self.result.iloc[0,6])
        gapTimeStamp /= 1000
        timearr = datetime.fromtimestamp(gapTimeStamp)
        otherStyleTime = datetime.strftime(timearr,"%M:%S.%f")[:-3]
        timeGap = str("+"+otherStyleTime)
        self.result.iloc[self.renewOrder,7] = timeGap
        #print(self.result[['code','lap','time','milliseconds','timeGap','selfComparison','tyreCondition']])
        
    def findPosition(self,newestRecord):
        if len(self.result['lap']) == 0:
            return 0
        else:
            for i, value in enumerate(self.result['lap'].tolist()):
                if int(newestRecord['lap']) > int(value) :
                    return i
            return len(set(self.result['code']))
        
    def tyreCondition(self,inputDataFrame):
        allTyreChoice = str()
        for key,value in self.pitTimes.items():
            if key == inputDataFrame.iloc[0,0]:
                driverTyreInfo = tyreChoice[tyreChoice['raceId'].isin([self.raceId]) & tyreChoice['code'].isin([key])]
                expectedLapsOnTyre = re.search(r'\d+',str(driverTyreInfo.iloc[0,2+value])).group()
                currentTyre = re.search(r'^[a-zA-Z]*\s*[a-zA-Z]*',str(driverTyreInfo.iloc[0,2+value])).group()
                if int(inputDataFrame.iloc[0,2]) == self.lastPit[key] + int(expectedLapsOnTyre):
                    allTyreChoice = str(int(inputDataFrame.iloc[0,2])-self.lastPit[key])+" "+currentTyre+'\033[35m PIT\033[0m'
                    self.pitTimes[key] += 1
                    self.lastPit[key] = int(inputDataFrame.iloc[0,2])
                else:
                    allTyreChoice = str(int(inputDataFrame.iloc[0,2])-self.lastPit[key])+" "+currentTyre 
        return allTyreChoice  
    
    def timeTransformer(self,inputTime):
        inputTime /= 1000
        timearr = datetime.fromtimestamp(inputTime)
        otherStyleTime = datetime.strftime(timearr,"%M:%S.%f")[:-3]
        outputTime = str(otherStyleTime)
        return outputTime
    
    def vscTimeGenerator(self):
        timeCostsKeys = list(self.timeCosts.keys())
        for i,key in enumerate(timeCostsKeys):
            expectedNextPassTime = self.timeCosts[key]
            self.timeCosts[key] -= self.driverNextLapTime[key]
            if 0 <= expectedNextPassTime - self.vscStart[self.vscTimes] < self.vscLast[self.vscTimes] :
                self.driverNextLapTime[key] = int(hamLTG.virtualSafetyCar(self.driverNextLapTime[key],self.vscStart[self.vscTimes],self.vscStart[self.vscTimes], expectedNextPassTime - self.vscStart[self.vscTimes],key))
            elif expectedNextPassTime - self.vscStart[self.vscTimes] >= self.vscLast[self.vscTimes]:
                self.driverNextLapTime[key] = int(hamLTG.virtualSafetyCar(self.driverNextLapTime[key],self.vscStart[self.vscTimes],self.vscStart[self.vscTimes],self.vscLast[self.vscTimes],key))
            self.timeCosts[key] += self.driverNextLapTime[key]
            self.raceData.loc[(self.raceData['code']== key) & (self.raceData['raceId']==self.raceId) & (self.raceData['lap']==self.lap[key]), 'milliseconds'] =  self.driverNextLapTime[key]
    
    def safetyFlagJudgment(self,value):
        tempVscFlag = False
        if not self.vscFlag:
            for i,v in enumerate(self.vscStart):
                if 0 <= value - v < self.vscLast[i]:
                    self.vscFlag = True
                    self.vscTimes = i
                    if i > 0:
                        tempVscFlag = True
                    break
        if self.vscFlag:
            if value - self.vscStart[self.vscTimes] >= self.vscLast[self.vscTimes]:
                self.vscFlag = False
        if tempVscFlag:
            tempVscFlag = False
            self.vscTimeGenerator()
     
    def fun_timer(self):
        while 1:
            if self.finalResultFlag:
                break
            self.dropFlag = False
            timeCostsValues = list(self.timeCosts.values())
            timeCostsKeys = list(self.timeCosts.keys())
            value = timeCostsValues[0]
            key = timeCostsKeys[0]
            self.safetyFlagJudgment(value)
            thisLap = self.raceData[self.raceData['lap'].isin([self.lap[key]])]
            thisLap = thisLap.reset_index(drop=True)
            if(self.lap[key] == 56):
                self.raceEndFlag = True
            self.output(thisLap[thisLap['code'] == key], key)
            self.endJudgement(key)
            self.nextLap(key)
            if self.dropFlag:
                for racer in self.dropRacer:
                    del self.driverNextLapTime[racer]
                    del self.timeCosts[racer]
                    del self.lap[racer]
            self.dropRacer = list()
            self.timeCosts = dict(sorted(self.timeCosts.items(), key=lambda x: x[1]))
            
    def endJudgement(self,key):
        if((key == self.player) & (self.raceEndFlag)):
            position = list(self.result['code']).index(self.player)+1
            timeCost = self.timeCosts[self.player]
            gapTime = int(timeCost) - int(self.result.iloc[0,6])
            print("The race ended. You are "+ str(position))
            print("Total time cost: "+str(timeCost))
            print("The gap between you and the 1st: "+str(gapTime))
            print("You overtook "+str(self.overtakeCount)+" opponent(s)")
            print("You were overtaken by "+str(self.beOvertakenCount)+" opponent(s)")
            positionGlobal.append(position)
            timeCostGlobal.append(timeCost)
            gapGlobal.append(gapTime)
            overtakeGlobal.append(self.overtakeCount)
            beOvertakenGlobal.append(self.beOvertakenCount)
            self.finalResultFlag = True
            
    def nextLap(self,key):
        nextLap = self.raceData[self.raceData['lap'].isin([self.lap[key]+1])]
        nextLap = nextLap.reset_index(drop=True)
        if key in set(nextLap['code']):
            if key in self.fastDrivers:
               if key in self.fastDrivers:
                if (self.lap[key] == self.lastPit[key]):
                    outLapTime = self.raceData[(self.raceData['code'] == key) & (self.raceData['raceId']==self.raceId) & (self.raceData['lap']==self.lap[key]+1)].iloc[0,5]
                    if self.vscFlag:  
                        currentTime = self.timeCosts[key]+self.pitLaneTime[key]
                        outTime = outLapTime-self.pitLaneTime[key]
                        affectedOutlapTime = int(hamLTG.virtualSafetyCar(outTime,currentTime,self.vscStart[self.vscTimes],self.vscLast[self.vscTimes],key))
                        self.driverNextLapTime[key] = self.pitLaneTime[key] +  affectedOutlapTime
                    else:    
                        self.driverNextLapTime[key] = outLapTime
                    self.raceData.loc[(self.raceData['code']== key) & (self.raceData['raceId']==self.raceId) & (self.raceData['lap']==self.lap[key]+1), 'milliseconds'] =  self.driverNextLapTime[key]
                    self.timeCosts[key] += self.driverNextLapTime[key]                   
                    self.lap[key] += 1                                                                                        
                else:
                    driverTyreInfo = tyreChoice[tyreChoice['raceId'].isin([self.raceId]) & tyreChoice['code'].isin([key])]
                    currentTyre = str(re.search(r'^[a-zA-Z]*\s*[a-zA-Z]*',str(driverTyreInfo.iloc[0,2+self.pitTimes[key]])).group())
                    expectedLapsOnTyre = int(re.search(r'\d+',str(driverTyreInfo.iloc[0,2+self.pitTimes[key]])).group())
                    currentTyre = currentTyre.strip()
                    if currentTyre == 'Used medium':
                        self.driverNextLapTime[key] = int(hamLTG.lapTimeUsedMedium(self.lap[key]-self.lastPit[key]+1,key))
                    elif currentTyre == 'Used soft':
                        self.driverNextLapTime[key] = int(hamLTG.lapTimeUsedSoft(self.lap[key]-self.lastPit[key]+1,key))
                    elif currentTyre == 'Soft': 
                        self.driverNextLapTime[key] = int(hamLTG.lapTimeNewSoft(self.lap[key]-self.lastPit[key]+1,key))
                    elif currentTyre == 'Medium':
                        self.driverNextLapTime[key] = int(hamLTG.lapTimeNewMedium(self.lap[key]-self.lastPit[key]+1,key))
                    elif currentTyre == 'Hard':
                        self.driverNextLapTime[key] = int(hamLTG.lapTimeNewHard(self.lap[key]-self.lastPit[key]+1,key))
                    if self.lap[key]-self.lastPit[key] == expectedLapsOnTyre-1:
                        self.driverNextLapTime[key] = int(hamLTG.pitTimeGenerate(self.driverNextLapTime[key],'','in',key))
                        nextTyre = str(re.search(r'^[a-zA-Z]*\s*[a-zA-Z]*',str(driverTyreInfo.iloc[0,3+self.pitTimes[key]])).group())
                        nextTyre = nextTyre.strip()
                        temp = hamLTG.pitTimeGenerate(0,nextTyre,'out',key)
                        self.pitLaneTime[key] = int(temp['lane'])
                        sumTime = int(temp['lane']+temp['out'])
                        self.raceData.loc[(self.raceData['code']== key) & (self.raceData['raceId']==self.raceId) & (self.raceData['lap']==self.lap[key]+2), 'milliseconds'] = sumTime
                    if self.vscFlag:  
                        self.driverNextLapTime[key] = int(hamLTG.virtualSafetyCar(self.driverNextLapTime[key],self.timeCosts[key],self.vscStart[self.vscTimes],self.vscLast[self.vscTimes],key))
                    else:
                        self.overtake(key)
                        self.overLap(key)
                    self.raceData.loc[(self.raceData['code']== key) & (self.raceData['raceId']==self.raceId) & (self.raceData['lap']==self.lap[key]+1), 'milliseconds'] =  self.driverNextLapTime[key]
                    self.timeCosts[key] += self.driverNextLapTime[key]
                    self.lap[key] += 1                      
            else:
                self.driverNextLapTime[key] = nextLap[nextLap['code'] == key].iloc[0,5]
                if self.vscFlag and self.vscTimes > 0:
                    self.driverNextLapTime[key] = int(hamLTG.virtualSafetyCar(self.driverNextLapTime[key],self.timeCosts[key],self.vscStart[self.vscTimes],self.vscLast[self.vscTimes],key))
                self.raceData.loc[(self.raceData['code']== key) & (self.raceData['raceId']==self.raceId) & (self.raceData['lap']==self.lap[key]+1), 'milliseconds'] =  self.driverNextLapTime[key]
                self.timeCosts[key] += self.driverNextLapTime[key]
                self.lap[key] += 1
        else:
            self.dropFlag = True
            self.dropRacer.append(key)
    
    def overtake(self,key):
        pursuerLoc = pd.Index(list(self.result['code'])).get_loc(key)
        leader = str(self.result.iloc[pursuerLoc-1,0])
        if pursuerLoc == 0 or leader not in self.driverNextLapTime.keys():
            return    
        gap = int(self.result.iloc[pursuerLoc,6]-self.result.iloc[pursuerLoc-1,6])
        adv = int(self.driverNextLapTime[leader]-self.driverNextLapTime[key])  
        if not self.raceEndFlag and (adv-gap > 0) and (gap < 1000)  and not (self.lap[leader] == self.lastPit[leader] + 1) and not pursuerLoc == 0:
            overtakeCompensation = otkCalculator.overtakeJudgement(gap,adv)
            self.driverNextLapTime[key] += overtakeCompensation['pursuer']
            self.driverNextLapTime[leader] += overtakeCompensation['leader']
            self.timeCosts[leader] += overtakeCompensation['leader']
            if key == self.player and adv - gap + overtakeCompensation['leader'] - overtakeCompensation['pursuer'] > 0:
                self.overtakeCount += 1
            elif leader == self.player and adv - gap + overtakeCompensation['leader'] - overtakeCompensation['pursuer'] > 0:
                self.beOvertakenCount += 1
            
    def overLap(self,key):
        currentRacerLoc = pd.Index(list(self.result['code'])).get_loc(key)
        follower = list(self.result['code'])[currentRacerLoc+1:]
        for followerKey,value in self.timeCosts.items():
            if (followerKey in follower) and (value > self.timeCosts[key] + self.driverNextLapTime[key]):
                overlapCompensation = olpCalculator.overlapJudgement()
                self.driverNextLapTime[key] += overlapCompensation['fast']
                if followerKey in self.fastDrivers:
                    self.timeCosts[followerKey] += overlapCompensation['slow']

def main():
    for i in range(100):
        race2019 = Race(1012,"VER") 
    print(positionGlobal)
    print(timeCostGlobal)
    print(gapGlobal)
    print(overtakeGlobal)
    print(beOvertakenGlobal)
    
if __name__ == '__main__':
    main()