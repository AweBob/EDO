import datetime
import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()
FACTION_ID = os.getenv('FACTION_ID')
FACTION_NAME = os.getenv('FACTION_NAME').lower()
DEBUG = os.getenv('DEBUG')

req_faction = FACTION_NAME.replace(' ', '%20')
req_uri = 'https://elitebgs.app/api/ebgs/v4/'


class Cache:
    def faction_update(self):
        faction_json = requests.get(f"{req_uri}factions?name={req_faction}")
        faction_json_data = json.loads(faction_json.text)

        if DEBUG:
            print(f'"Faction" reply: {faction_json_data}')

        if not faction_json_data['docs']:
            with open('err.log', 'a+') as err_log:
                print(f'{datetime.datetime.now()}, Bad faction name: {req_faction}')
                err_log.write(f'{datetime.datetime.now()}, Bad faction name: {req_faction}')

        return faction_json_data

    def get_conflicts_active(self, faction_data):
        report = {}
        for system in faction_data['docs'][0]['faction_presence']:
            for state in system['active_states']:
                if (
                        state['state'] == 'war' or
                        state['state'] == 'civil war' or
                        state['state'] == 'election'
                ):
                    system_name_lower = system['system_name_lower'].replace(' ', '%20')
                    system_json = requests.get(f"{req_uri}systems?name={system_name_lower}")
                    system_json_data = json.loads(system_json.text)

                    if DEBUG:
                        print(f'"Active conflict system" reply: {system_json_data}')

                    for conflict in system_json_data['docs'][0]['conflicts']:
                        if (
                                conflict['status'] == 'active' and
                                (
                                        conflict['faction1']['name_lower'] == FACTION_NAME or
                                        conflict['faction2']['name_lower'] == FACTION_NAME
                                )
                        ):
                            if conflict['faction1']['name_lower'] == FACTION_NAME:
                                us = 'faction1'
                                them = 'faction2'
                            else:
                                us = 'faction2'
                                them = 'faction1'
                            report[system['system_name']] = {
                                'state': state['state'],
                                'enemy': conflict[them]['name'],
                                'score_us': conflict[us]["days_won"],
                                'score_them': conflict[them]["days_won"],
                                'win': conflict[them]['stake'],
                                'loss': conflict[us]['stake'],
                                'updated_at': system['updated_at']
                            }
        return report

    def get_conflicts_recovering(self, faction_data):
        report = {}
        for system in faction_data['docs'][0]['faction_presence']:
            for state in system['recovering_states']:
                if (
                        state['state'] == 'war' or
                        state['state'] == 'civil war' or
                        state['state'] == 'election'
                ):
                    opponent_name = system['conflicts'][0]['opponent_name']
                    opp_faction_json = requests.get(f"{req_uri}factions?name={opponent_name}")
                    opp_faction_json_data = json.loads(opp_faction_json.text)

                    for opp_system in opp_faction_json_data['docs'][0]['faction_presence']:
                        if opp_system['conflicts'][0]['opponent_name_lower'] == FACTION_NAME:
                            days_won = system['conflicts'][0]['days_won']
                            opp_days_won = opp_system['conflicts'][0]['days_won']
                            win, loss = '', ''
                            if days_won > opp_days_won:
                                status = 'Victory'
                                win = system['conflicts'][0]['stake']
                            else:
                                status = 'Defeat'
                                loss = opp_system['conflicts'][0]['stake']
                            report[system['system_name']] = {
                                'status': status,
                                'days_won': days_won,
                                'days_lost': opp_days_won,
                                'win': win,
                                'loss': loss,
                                'updated_at': system['updated_at']
                            }
        print('"Recovering report"', report)
        return report

    def get_conflicts_pending(self, faction_data):
        pass

    def __init__(self):
        self.faction_data = self.faction_update()
        self.conflicts_active = self.get_conflicts_active(self.faction_data)
        self.conflicts_recovering = self.get_conflicts_recovering(self.faction_data)
        self.conflicts_pending = self.get_conflicts_pending(self.faction_data)
