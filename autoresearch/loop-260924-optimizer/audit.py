"""Independent marked-zero projection and expanded-component certificate audit."""
import json,sys,zipfile
from pathlib import Path
from functools import lru_cache
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parents[1]))
from src.lrx.certificates import CertificateValidator
from integrations.projected_mixtures import comparison,materialize,verify_mixture
with zipfile.ZipFile(P.parents[1]/'autoresearch/loop-260923-2107/incoming/verification.zip') as z:
    catalog=json.loads(z.read('literature/multiset_nine_gap_complete_certificates_20260924.json'))['catalog']
@lru_cache(None)
def projected(i,mask):
    state=tuple(catalog[i]['state']);word=catalog[i]['word']
    for gap in reversed(range(9)):
        if mask>>gap&1:continue
        j=2*gap;u=state[:j]+state[j+1:]
        result=CertificateValidator(8,len(state)-8).replay_word(word,start_state=(u,j))
        assert result.replay_valid and result.terminal
        word=result.projection_sequence;state=u
    reduced=[]
    for c in word:
        if reduced and (reduced[-1],c) in (('L','R'),('R','L')):reduced.pop()
        else:reduced.append(c)
    return state,''.join(reduced)

def audit(rows):
    families=components=replays=0
    for row in rows:
        cert=row['certificate']
        if not cert:continue
        profiles=[];weights=[]
        for support in cert['support']:
            p=support['profile']
            if 'source' in p:
                state,word=projected(p['source'],row['case']['mask'])
                assert state==tuple(p['state']) and word==p['word']
            q=comparison(tuple(p['state']),p['word'],p['cut'],[x for x in p['target'] if x])
            assert q is not None and q['base']==p['base'] and q['gamma']==p['gamma']
            profiles.append(q);weights.append(support['weight']);components+=1;k=len(q['gamma'])
            for lengths in [[1]*k]+[[1+int(i==j) for i in range(k)] for j in range(k)]+[[2+i%3 for i in range(k)]]:
                materialize(q,lengths);replays+=1
        assert verify_mixture(profiles,weights)==cert['bounds'];families+=1
    return dict(certified=families,components=components,expanded_replays=replays)

if __name__=='__main__':
    result={'baseline':audit(json.loads((P/'baseline-results.json').read_text()))}
    confirmation=P/'confirmation-results.json'
    if confirmation.exists():
        data=json.loads(confirmation.read_text());result['confirmation_baseline']=audit(data['baseline'])
        for arm,r in data['arms'].items():result['confirmation_'+arm]=audit(r['cases'])
    for arm in ('sequential','evox'):
        summary=P/(arm+'-run')/'summary.json'
        if summary.exists():
            best=json.loads(summary.read_text())['best']['hash']
            r=json.loads((summary.parent/'evals'/f'{best}.json').read_text());result['train_'+arm]=audit(r['cases'])
    (P/'audit-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
