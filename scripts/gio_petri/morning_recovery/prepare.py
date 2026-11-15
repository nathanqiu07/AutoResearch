"""Create a frozen single or matched-arm morning packet without model calls."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from morning_recovery.packet import prepare_packet

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contexts',nargs='+',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--start-time',required=True)
    p.add_argument('--lease',required=True,type=Path)
    p.add_argument('--authoring-contract',type=Path)
    a=p.parse_args()
    settings=prepare_packet(a.contexts,a.out,a.start_time,json.loads(a.lease.read_text()),a.authoring_contract)
    print(json.dumps({'packet':str(a.out),'arms':settings['arms'],'model_calls':0}))

if __name__=='__main__':main()
