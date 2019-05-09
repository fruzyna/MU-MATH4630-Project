# imports
import pandas as pd
import random as rd
import concurrent.futures
from statistics import mean

# function for improved logging
printLogs = False
def log(*objs, force=False):
    if force or printLogs:
        strs = []
        for obj in objs:
            strs.append(str(obj))
        print(' '.join(strs))
        
# read in and format batting data
b = pd.read_csv('Batting.csv')
b = b[b['yearID'] == 1968]
b['1B'] = b['H'] - b['2B'] - b['3B'] - b['HR']
b['O'] = b['AB'] - (b['H'] + b['SO'])
b['PA'] = b['AB'] + b['BB']
b = b[['playerID', 'teamID', 'lgID', 'PA', 'H', '1B', '2B', '3B', 'HR', 'BB', 'SO', 'O']]

# convert batting data to percentages
bp = b.copy()
bp['H'] = b['H'] / b['PA']
bp['BB'] = b['BB'] / b['PA']
bp['SO'] = b['SO'] / b['PA']
bp['O'] = b['O'] / b['PA']
bp['1B'] = b['1B'] / b['PA']
bp['2B'] = b['2B'] / b['PA']
bp['3B'] = b['3B'] / b['PA']
bp['HR'] = b['HR'] / b['PA']

# read in and format pitching data
p = pd.read_csv('Pitching.csv')
p = p[p['yearID'] == 1968]
p['O'] = p['BFP'] - (p['H'] + p['BB'] + p['SO'])
p = p[['playerID', 'teamID', 'lgID', 'BFP', 'H', 'HR', 'BB', 'SO', 'O']]

# convert pitching data to percentages
pp = p.copy()
pp['H'] = p['H'] / p['BFP']
pp['BB'] = p['BB'] / p['BFP']
pp['SO'] = p['SO'] / p['BFP']
pp['O'] = p['O'] / p['BFP']
pp['HR'] = p['HR'] / p['BFP']

# get a list of teams and franchise info
teamIds = b['teamID'].unique()

# build a roster of 8 batters and a pitcher for each team
teams = {}
for team in teamIds:
    # find single most used pitched (batters faced)
    pitchers = pp[pp['teamID'] == team]
    pitcher = pitchers.nlargest(1, columns=['BFP']).iloc[0]
    teams[team + '-pitcher'] = pitcher
    # find top 8 most used batters (at bats), plus pitcher
    batters = bp[bp['teamID'] == team]
    pitcherBat = batters[batters['playerID'] == pitcher['playerID']]
    teams[team + '-batters'] = batters.nlargest(8, columns=['PA']).append(pitcherBat)
    
# function to build a list of odds into a list of brackets
def sumOdds(odds):
    for i in range(1, len(odds)):
        odds[i] += odds[i-1]
    return odds

# object to track and manage which bases are occupied
class Bases:
    def __init__(self):
        self.bases = [False, False, False, False]
        self.runs = 0
        
    def __repr__(self):
        bases = ''
        for b in range(1, 4):
            if self.bases[b]:
                bases += ' ' + str(b)
        return str(self.runs) + ' scored with men on' + bases
        
    # simulate a hit on the bases
    def play(self, earned):
        log('Bases:', earned)
        if earned > 0:
            for b in range(len(self.bases)-1, 0, -1):
                if self.bases[b]:
                    reached = b + earned
                    self.bases[b] = False
                    if reached >= 4:
                        self.runs += 1
                    else:
                        self.bases[reached] = True
            if earned == 4:
                self.runs += 1
            else:
                self.bases[earned] = True
                
# process a single at bat of a pitcher vs a batter
def runAtBat(batter, pitcher):
    log('Batting:', batter['playerID'])
    # calculate odds
    odds = sumOdds([mean([batter['1B'], pitcher['H']/4]), mean([batter['2B'], pitcher['H']/4]), 
                    mean([batter['3B'], pitcher['H']/4]), mean([batter['HR'], pitcher['HR']]), 
                    mean([batter['BB'], pitcher['BB']]), mean([batter['SO'], pitcher['SO']])])
    log(odds)
    
    # randomly choose a play
    play = rd.random()
    if play <= odds[0]:
        log('Single')
        return 1, 0
    elif play <= odds[1]:
        log('Double')
        return 2, 0
    elif play <= odds[2]:
        log('Triple')
        return 3, 0
    elif play <= odds[3]:
        log('Home Run')
        return 4, 0
    elif play <= odds[4]:
        log('Base on Balls')
        return 1, 0
    elif play <= odds[5]:
        log('Strike Out')
        return 0, 1
    log('Out')
    return 0, 1

# run a single side of an inning (3 outs)
def runInning(offTeam, defTeam, leadOff):
    lineup = teams[offTeam + '-batters']
    pitcher = teams[defTeam + '-pitcher']
    bnum = leadOff
    outs = 0
    bases = Bases()
    # run until 3 outs are obtained
    while outs < 3:
        # get the next batter up and run the at bat
        batter = lineup.iloc[bnum]
        b, o = runAtBat(batter, pitcher)
        bases.play(b)
        outs += o
        bnum += 1
        log(bases)
        if bnum >= 9:
            bnum = 0
    return bases.runs, bnum

# run a single game, a home team against a visitor
def runGame(homeTeam, awayTeam):
    home = 0
    away = 0
    inning = 1
    homeNext = 0
    awayNext = 0
    # run until at least 9 innings are complete and a team has a higher score
    while inning <= 9 or home == away:
        # run the top of the inning
        log('---')
        log('Top', inning)
        r, n = runInning(awayTeam, homeTeam, awayNext)
        away += r
        awayNext = n
        # run the bottom of the inning
        log('---')
        log('Bottom', inning)
        r, n = runInning(homeTeam, awayTeam, homeNext)
        home += r
        homeNext = n
        inning += 1
    # mark the winner
    winner = 'HOME'
    if home < away:
        winner = 'AWAY'
    return home, away, winner

# play a series of games between 2 teams
def runSeries(home, away, games, seriesLen):
    # run all the games in the series
    for i in range(seriesLen):
        log(away, '@', home, '#' + str(i+1))
        # run game
        games['homeTeam'].append(home)
        games['awayTeam'].append(away)
        h, a, w = runGame(home, away)
        # log score
        games['homeScore'].append(h)
        games['awayScore'].append(a)
        games['winner'].append(w)
        log('Final:', h, a)
        log('')
        
# process a while league of teams, assuming a certain amount of home games against each team in the league
def runLeague(teams, seriesLen):
    games = {'homeTeam': [], 'awayTeam': [], 'homeScore': [], 'awayScore': [], 'winner': []}
    for home in teams:
        for away in teams:
            if home != away:
                runSeries(home, away, games, seriesLen)
    return pd.DataFrame(data=games)

# process a while league of teams, assuming a certain amount of home games against each team in the league
def runPlayoff(teamA, teamB):
    games = {'homeTeam': [], 'awayTeam': [], 'homeScore': [], 'awayScore': [], 'winner': []}
    # determine who has home team advantage
    teams = pd.concat([teamA, teamB], axis=1).T.sort_values(by=['wins', 'homeWins', 'awayWins', 'team'], ascending=False)
    teamA = teams['team'].iloc[0]
    teamB = teams['team'].iloc[1]
    # 4 home games and 3 away for the better team
    runSeries(teamA, teamB, games, 4)
    runSeries(teamB, teamA, games, 3)
    return pd.DataFrame(data=games)

# generate a leaderboard for a given set of teams
def standings(league):
    board = {'team': [], 'wins': [], 'losses': [], 'homeWins': [], 'homeLosses': [], 'awayWins': [], 'awayLosses': []}
    # add each team
    for team in league['homeTeam'].unique():
        homeGames = league[league['homeTeam'] == team]
        homeWins = len(homeGames[homeGames['winner'] == 'HOME'].index)
        awayGames = league[league['awayTeam'] == team]
        awayWins = len(awayGames[awayGames['winner'] == 'AWAY'].index)
        totalGames = len(homeGames.index) + len(awayGames.index)
        board['team'].append(team)
        board['wins'].append(homeWins + awayWins)
        board['losses'].append(totalGames - (homeWins + awayWins))
        board['homeWins'].append(homeWins)
        board['homeLosses'].append(len(homeGames.index) - homeWins)
        board['awayWins'].append(awayWins)
        board['awayLosses'].append(len(awayGames.index) - awayWins)
    # sort standings (best at top)
    return pd.DataFrame(data=board).sort_values(by=['wins', 'homeWins', 'awayWins', 'team'], ascending=False)

# returns the best team in a standings 
def getWinner(standings):
    return standings.iloc[0]

# number of season to simluate per process
threads = 5
seasons = 200

# run a number of complete season
def runSeasons(thread, seasons):
    winners = []
    for i in range(seasons):
        print(thread, i)
        # run each league
        national = runLeague(b.loc[b['lgID'] == 'NL']['teamID'].unique(), 9)
        american = runLeague(b.loc[b['lgID'] == 'AL']['teamID'].unique(), 9)
        # calculate standings
        nlstand = standings(national)
        alstand = standings(american)
        # run world series
        ws = runPlayoff(getWinner(nlstand), getWinner(alstand))
        worldstand = standings(ws)
        # log champion
        winners.append(getWinner(worldstand)['team'])
    print(t, winners)

# run across multiple processes
executor = concurrent.futures.ProcessPoolExecutor(threads)
winners = [executor.submit(runSeason, i, seasons) for i in range(threads)]
concurrent.futures.wait(winners)