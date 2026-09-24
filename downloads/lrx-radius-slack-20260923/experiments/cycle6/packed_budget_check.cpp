// Independent checker: literal nibble words, binary-search IDs, and full-length
// slack DP. Does not include or call radius_slack.cpp or its multiset ranker.
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
constexpr uint8_t INF=255;
struct LiteralGraph {
 int m,r,n;uint64_t mask,root;vector<uint64_t>states;
 vector<array<uint32_t,3>>edge;vector<uint8_t>dist;vector<uint32_t>order;
 uint64_t pack(const vector<int>&v)const{uint64_t s=0;for(int x:v)s=(s<<4)|x;return s;}
 vector<int> unpack(uint64_t s)const{vector<int>a(n);for(int i=n-1;i>=0;--i){a[i]=s&15;s>>=4;}return a;}
 uint32_t id(uint64_t s)const{auto it=lower_bound(states.begin(),states.end(),s);if(it==states.end()||*it!=s)throw runtime_error("literal state absent");return uint32_t(it-states.begin());}
 array<uint64_t,3> moves(uint64_t s)const{
  auto diff=((s>>(4*(n-1)))^(s>>(4*(n-2))))&15;
  return {((s<<4)&mask)|(s>>(4*(n-1))), (s>>4)|((s&15)<<(4*(n-1))),s^(diff<<(4*(n-1)))^(diff<<(4*(n-2)))};
 }
 LiteralGraph(int mm,int rr):m(mm),r(rr),n(m+r){
  if(n>12||m<2||r<1)throw runtime_error("unsupported literal graph");mask=(1ULL<<(4*n))-1;
  uint64_t count=1;for(int i=r+1;i<=n;++i)count*=i;
  if(count>25000000)throw runtime_error("independent checker limited to 25 million vertices");states.reserve(count);
  vector<int>a(r,0);for(int i=1;i<=m;++i)a.push_back(i);
  do{states.push_back(pack(a));}while(next_permutation(a.begin(),a.end()));
  if(states.size()!=count||!is_sorted(states.begin(),states.end()))throw runtime_error("bad enumeration");
  for(size_t i=1;i<states.size();++i)if(states[i]==states[i-1])throw runtime_error("duplicate state");
  a.clear();for(int i=1;i<=m;++i)a.push_back(i);a.resize(n,0);root=pack(a);
  edge.resize(count);
  for(size_t i=0;i<count;++i){auto v=moves(states[i]);for(int op=0;op<3;++op)edge[i][op]=id(v[op]);}
  // Each labelled edge must have its literal inverse.
  for(size_t u=0;u<count;++u)if(edge[edge[u][0]][1]!=u||edge[edge[u][1]][0]!=u||edge[edge[u][2]][2]!=u)throw runtime_error("inverse-edge failure");
  dist.assign(count,INF);order.reserve(count);auto rt=id(root);dist[rt]=0;order.push_back(rt);
  for(size_t h=0;h<order.size();++h){auto u=order[h];if(dist[u]>=253)throw runtime_error("distance byte limit");for(auto v:edge[u])if(dist[v]==INF){dist[v]=dist[u]+1;order.push_back(v);}}
  if(order.size()!=count)throw runtime_error("BFS incomplete");
 }
};
struct Step{int slot,projected;};
Step marked_step(const vector<int>&v,const vector<int>&positions,int slot,int op){
 int r=positions.size(),n=v.size(),j=positions[slot],next=slot,cost=1;
 if(op==0){if(v.front()==0)next=(slot+r-1)%r;cost=j!=0;}
 if(op==1){if(v.back()==0)next=(slot+1)%r;cost=j!=n-1;}
 if(op==2){if(v[0]==0&&v[1]==0&&slot<2)next=1-slot;cost=!(j<2||(v[0]==0&&v[1]==0));}
 return {next,cost};
}
void printvec(const vector<int>&v){cout<<'[';for(size_t i=0;i<v.size();++i){if(i)cout<<',';cout<<v[i];}cout<<']';}
int main(int argc,char**argv){try{
 if(argc<3)throw runtime_error("usage: packed_budget_check m r [extra=2]");int m=stoi(argv[1]),r=stoi(argv[2]),extra=argc>3?stoi(argv[3]):2;
 if(r<2||extra<0||extra>4)throw runtime_error("bad resource bound");
 auto start=chrono::steady_clock::now();int P;uint64_t smaller;
 {LiteralGraph small(m,r-1);P=*max_element(small.dist.begin(),small.dist.end());smaller=small.states.size();}
 LiteralGraph g(m,r);size_t N=g.states.size(),S=N*r;
 if(N*25+S*(extra+1)>600000000)throw runtime_error("memory cap 600 MB");
 vector<vector<uint8_t>>Q(extra+1,vector<uint8_t>(S,INF));vector<map<int,uint64_t>>hist(extra+1);
 vector<uint64_t>over(extra+1,0);vector<uint32_t>exceptional;
 for(int e=0;e<=extra;++e){
  if(e)Q[e]=Q[e-1];auto rt=g.id(g.root);for(int j=0;j<r;++j)Q[e][size_t(rt)*r+j]=0;
  for(auto u:g.order){auto v=g.unpack(g.states[u]);vector<int>positions;for(int j=0;j<g.n;++j)if(v[j]==0)positions.push_back(j);
   for(int op=0;op<3;++op){auto to=g.edge[u][op];int spent=1+int(g.dist[to])-int(g.dist[u]);if(spent<0||spent>2)throw runtime_error("non-Lipschitz BFS");if(spent>e)continue;
    for(int slot=0;slot<r;++slot){auto step=marked_step(v,positions,slot,op);int val=int(Q[e-spent][size_t(to)*r+step.slot])+step.projected;auto&cell=Q[e][size_t(u)*r+slot];if(val<cell)cell=val;}
   }
   int best=INF;for(int slot=0;slot<r;++slot)best=min(best,int(Q[e][size_t(u)*r+slot]));
   ++hist[e][best];if(best>P){++over[e];if(e==0&&exceptional.size()<128)exceptional.push_back(u);}
  }cerr<<"m="<<m<<" r="<<r<<" full_extra="<<e<<" projection_over_P="<<over[e]<<'\n';
 }
 auto buildword=[&](uint32_t u,int slot,int e){string word;
  for(int guard=0;guard<300;++guard){if(g.states[u]==g.root)return word;
   int value=Q[e][size_t(u)*r+slot];if(e&&Q[e-1][size_t(u)*r+slot]==value){--e;continue;}
   auto v=g.unpack(g.states[u]);vector<int>positions;for(int j=0;j<g.n;++j)if(v[j]==0)positions.push_back(j);bool found=false;
   for(int op=0;op<3&&!found;++op){auto to=g.edge[u][op];int spent=1+int(g.dist[to])-int(g.dist[u]);if(spent>e)continue;auto step=marked_step(v,positions,slot,op);
    if(int(Q[e-spent][size_t(to)*r+step.slot])+step.projected==value){word+="LRX"[op];u=to;slot=step.slot;e-=spent;found=true;}}
   if(!found)throw runtime_error("cannot reconstruct minimal projection");
  }throw runtime_error("word loop guard");
 };
 cout<<"{\"method\":\"literal packed words and full-length-slack DP\",\"m\":"<<m<<",\"r\":"<<r<<",\"P\":"<<P<<",\"smaller_states\":"<<smaller<<",\"full_states\":"<<N<<",\"full_radius\":"<<int(*max_element(g.dist.begin(),g.dist.end()))<<",\"layers\":[";
 for(int e=0;e<=extra;++e){if(e)cout<<',';cout<<"{\"extra_full_steps\":"<<e<<",\"over_P\":"<<over[e]<<",\"histogram\":{";bool first=true;for(auto [q,count]:hist[e]){if(!first)cout<<',';first=false;cout<<'"'<<q<<"\":"<<count;}cout<<"}}";}cout<<"],\"exceptional_states\":[";
 for(size_t i=0;i<exceptional.size();++i){if(i)cout<<',';auto u=exceptional[i];auto v=g.unpack(g.states[u]);vector<int>pos;for(int j=0;j<g.n;++j)if(v[j]==0)pos.push_back(j);
  cout<<"{\"v\":";printvec(v);cout<<",\"distance\":"<<int(g.dist[u])<<",\"layers\":[";
  for(int e=0;e<=extra;++e){if(e)cout<<',';vector<int>per;for(int t=0;t<r;++t)per.push_back(Q[e][size_t(u)*r+t]);int slot=min_element(per.begin(),per.end())-per.begin();auto word=buildword(u,slot,e);
   cout<<"{\"extra_full_steps\":"<<e<<",\"minimum_projection_per_mark\":";printvec(per);cout<<",\"marked_index\":"<<pos[slot]<<",\"minimum_projection\":"<<per[slot]<<",\"word\":\""<<word<<"\",\"word_length\":"<<word.size()<<'}';
  }cout<<"]}";
 }cout<<"],\"elapsed_seconds\":"<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<"}\n";
 }catch(exception&e){cerr<<"ERROR: "<<e.what()<<'\n';return 1;}}
