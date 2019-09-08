import subprocess
import json

import pandas as pd


class ReplayParsingError(Exception):
    pass


def parse(demo_path):
    # TODO: replace gosu parser
    java_parser = subprocess.run(
        [f'cat {demo_path} | java -cp clarity-parser/target/stats-0.1.0.jar ai.gosu.dota2.parser.MainCLI'], 
        shell=True, capture_output=True, text=True
    )
    json_lines = java_parser.stdout
    
    events_log = []
    game_zero = None
    for line in json_lines.split('\n'):
        if line:
            e = json.loads(line)
            if e['type'] == 'DOTA_COMBATLOG_GAME_STATE' and e['value'] == 5:
                game_zero = e['time']
            events_log.append(e)
            
    if not events_log:
        print(java_parser.stderr)
        raise ReplayParsingError
    if game_zero is None:
        raise ReplayParsingError('game_zero event not found...')
    return events_log, game_zero


class TransformerError(Exception):
    pass


def create_tiny_damage_dataset(demo_path):
    """Lesson 1"""
    events_log, game_zero = parse(demo_path)
    
    damage_log = []
    for e in events_log:
        _type = e['type']
        if _type == 'DOTA_COMBATLOG_DAMAGE' and e['targethero'] and e['attackerhero']:
            damage_log.append(e)
    
    df_damage = pd.DataFrame(damage_log)
    df_damage['time'] -= game_zero
    df_damage['minute'] = df_damage['time'] // 60
    df_tiny = df_damage.query('attackername == "npc_dota_hero_tiny"').reset_index(drop=True).copy()
    if df_tiny.empty:
        raise TransformerError('Tiny not found in the replay...')
    df_tiny = df_tiny[['time', 'minute', 'attackername', 'targetname', 'inflictor', 'value']]
    df_tiny.rename(columns=dict(time='timestamp', attackername='source', targetname='target'), inplace=True)
    df_tiny['timestamp'] = df_tiny['timestamp'].astype(int)
    df_tiny['inflictor'] = df_tiny['inflictor'].apply(lambda name: name.replace('dota_unknown', 'attack'))
    return df_tiny


def update_tiny_damage_dataset(demo_path='og-liquid-map3.dem', output_file='og-liquid-map-3-tiny-damage.csv'):
    """Lesson 1"""
    df_tiny = create_tiny_damage_dataset(demo_path)
    df_tiny.to_csv(output_file, index=False)
    