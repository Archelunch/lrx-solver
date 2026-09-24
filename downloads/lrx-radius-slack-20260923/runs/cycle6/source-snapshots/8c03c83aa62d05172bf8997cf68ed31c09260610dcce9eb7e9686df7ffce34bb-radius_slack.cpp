// Exact bounded-projection lifting. No third-party dependencies.
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
constexpr uint16_t INF=60000;
struct Graph {
 int m,z,n; uint32_t count; vector<uint64_t> fact; vector<uint8_t> states;
 vector<array<uint32_t,3>> adj;
 Graph(int mm,int zz,bool edges):m(mm),z(zz),n(mm+zz),fact(n+1,1) {
  if(n>18 || z<1 || m<2) throw runtime_error("unsupported parameters");
  for(int i=1;i<=n;++i)fact[i]=fact[i-1]*i;
  uint64_t total=fact[n]/fact[z];
  if(total>7000000)throw runtime_error("graph state limit exceeded");
  count=total; states.reserve(total*n);
  vector<uint8_t> a(z,0);for(int i=1;i<=m;++i)a.push_back(i);
  uint32_t id=0;
  do {if(rank(a.data())!=id++)throw runtime_error("rank enumeration mismatch");states.insert(states.end(),a.begin(),a.end());}while(next_permutation(a.begin(),a.end()));
  if(edges){adj.resize(count);for(uint32_t u=0;u<count;++u)adj[u]=neighbors(u);}
 }
 uint32_t rank(const uint8_t *a)const {
  uint64_t r=0;int zeros=z;uint32_t mask=(1u<<m)-1;
  for(int i=0;i<n;++i){int v=a[i],left=n-i-1;
   if(v){if(zeros)r+=fact[left]/fact[zeros-1];
    r+=uint64_t(__builtin_popcount(mask&((1u<<(v-1))-1)))*(fact[left]/fact[zeros]);
    mask&=~(1u<<(v-1));
   }else --zeros;
  }return uint32_t(r);
 }
 array<uint32_t,3> neighbors(uint32_t u)const {
  auto a=&states[size_t(u)*n];array<uint8_t,18>b{};
  for(int i=0;i<n;++i)b[i]=a[(i+1)%n];auto l=rank(b.data());
  for(int i=0;i<n;++i)b[i]=a[(i+n-1)%n];auto r=rank(b.data());
  copy(a,a+n,b.begin());swap(b[0],b[1]);return {l,r,rank(b.data())};
 }
 uint32_t root()const {array<uint8_t,18>a{};for(int i=0;i<m;++i)a[i]=i+1;return rank(a.data());}
 vector<uint16_t> distances()const {
  vector<uint16_t>d(count,INF);vector<uint32_t>q;q.reserve(count);d[root()]=0;q.push_back(root());
  for(size_t h=0;h<q.size();++h){auto u=q[h];auto nb=adj.empty()?neighbors(u):adj[u];for(auto v:nb)if(d[v]==INF){d[v]=d[u]+1;q.push_back(v);}}
  if(q.size()!=count)throw runtime_error("disconnected enumeration");return d;
 }
};
void printvec(const vector<uint8_t>&v){cout<<'[';for(size_t i=0;i<v.size();++i){if(i)cout<<',';cout<<int(v[i]);}cout<<']';}
int main(int argc,char**argv){try{
 if(argc<3)throw runtime_error("usage: radius_slack m r [--witness] [--full]");
 int m=stoi(argv[1]),r=stoi(argv[2]),n=m+r;bool witness=false,full=false;
 for(int i=3;i<argc;++i){string a=argv[i];if(a=="--witness")witness=true;else if(a=="--full")full=true;else throw runtime_error("bad option");}
 auto started=chrono::steady_clock::now();Graph g(m,r-1,true);
 if(g.count>3000000)throw runtime_error("smaller graph exceeds 3 million state cap");
 auto d=g.distances();int P=*max_element(d.begin(),d.end()),bound=P+m-2;
 size_t S=size_t(g.count)*n,predBytes=witness?S*(P+1):0;
 uint64_t estimate=predBytes+4*S+g.states.size()+12ull*g.count+6ull*g.count;
 if(full) estimate+=uint64_t(g.count)*n/r*(n+6);
 if(estimate>600000000)throw runtime_error("estimated memory exceeds 600MB cap");
 cerr<<"small_states="<<g.count<<" P="<<P<<" marked_states="<<S<<" estimated_bytes="<<estimate<<'\n';
 vector<uint16_t>prev(S,INF),cur(S,INF);vector<uint8_t>pred(predBytes,255);
 auto idx=[n](uint32_t u,int j){return size_t(u)*n+j;};
 auto closure=[&](uint16_t*row,uint8_t*choices){
  array<int,3>pos{0,1,n-1};array<uint16_t,3>a{row[0],row[1],row[n-1]};
  for(int f=0;f<3;++f)for(int t=0;t<3;++t)if(t!=f){int len=(f==0||t==0)?1:2;int val=int(a[t])+len;
   if(val<row[pos[f]]){row[pos[f]]=val;if(choices)choices[pos[f]]=f==1?3:(f==2?2:(t==1?3:1));}}
 };
 auto rt=g.root();for(int j=m;j<n;++j){prev[idx(rt,j)]=0;if(witness)pred[idx(rt,j)]=0;}
 closure(&prev[idx(rt,0)],witness?&pred[idx(rt,0)]:nullptr);
 for(int p=1;p<=P;++p){
  cur=prev;uint8_t*pr=witness?&pred[size_t(p)*S]:nullptr;
  if(pr)for(size_t s=0;s<S;++s)pr[s]=prev[s]<INF?4:255;
  for(uint32_t u=0;u<g.count;++u){auto nb=g.adj[u];auto base=idx(u,0);
   for(int j=0;j<n;++j){size_t here=base+j;auto offer=[&](uint32_t v,int k,uint8_t op){int val=1+int(prev[idx(v,k)]);if(val<cur[here]){cur[here]=val;if(pr)pr[here]=op;}};
    if(j>0)offer(nb[0],j-1,1);if(j<n-1)offer(nb[1],j+1,2);if(j>=2&&nb[2]!=u)offer(nb[2],j,3);
   }closure(&cur[base],pr?pr+base:nullptr);
  }prev.swap(cur);if(p%10==0||p==P)cerr<<"projection_budget="<<p<<'/'<<P<<'\n';
 }
 vector<uint16_t>fd;unique_ptr<Graph>fg;
 if(full){fg=make_unique<Graph>(m,r,false);fd=fg->distances();}
 struct Example{vector<uint8_t>v;uint32_t u;int j,cost,distance;};
 vector<Example>examples,violations;vector<uint64_t>hist(1,0),gapHist(1,0);uint64_t visible=0,missing=0,excess=0;int maxA=-1,maxGap=-1,fullRadius=full?*max_element(fd.begin(),fd.end()):-1;
 vector<uint8_t>v(r,0);for(int i=1;i<=m;++i)v.push_back(i);
 do{uint16_t best=INF;uint32_t bu=0;int bj=-1;array<uint8_t,18>u{};
  for(int j=0;j<n;++j)if(v[j]==0){int t=0;for(int k=0;k<n;++k)if(k!=j)u[t++]=v[k];auto id=g.rank(u.data());auto val=prev[idx(id,j)];if(val<best){best=val;bu=id;bj=j;}}
  int exact=full?fd[visible]:-1;Example ex{v,bu,bj,best,exact};
  if(best==INF){++missing;if(violations.size()<8)violations.push_back(ex);}else{
   if(best>maxA){maxA=best;examples.clear();}if(best==maxA&&examples.size()<4)examples.push_back(ex);
   if(hist.size()<=best)hist.resize(best+1,0);++hist[best];
   if(best>bound){++excess;if(violations.size()<8)violations.push_back(ex);}
   if(full){if(best<exact)throw runtime_error("lift shorter than exact distance");int gap=best-exact;maxGap=max(maxGap,gap);if(gapHist.size()<=size_t(gap))gapHist.resize(gap+1,0);++gapHist[gap];}
  }++visible;
 }while(next_permutation(v.begin(),v.end()));
 auto word=[&](Example ex){string w;uint32_t u=ex.u;int j=ex.j,p=P;if(j<0)return w;
  for(int guard=0;guard<2*(P+maxA+10);++guard){auto a=pred[size_t(p)*S+idx(u,j)];if(a==0){if(u!=rt||j<m)throw runtime_error("bad word endpoint");return w;}
   if(a==4){if(p==0)throw runtime_error("carry at zero");--p;continue;}auto nb=g.adj[u];uint32_t next=u;
   if(a==1){w+='L';if(j==0)j=n-1;else{next=nb[0];--j;}}
   else if(a==2){w+='R';if(j==n-1)j=0;else{next=nb[1];++j;}}
   else if(a==3){w+='X';if(j<2)j=1-j;else next=nb[2];}
   else throw runtime_error("invalid predecessor");
   if(next!=u){if(p==0)throw runtime_error("projection budget exhausted");--p;}u=next;
  }throw runtime_error("witness reconstruction limit");
 };
 auto printExamples=[&](const vector<Example>&exs){cout<<'[';for(size_t i=0;i<exs.size();++i){if(i)cout<<',';auto&ex=exs[i];cout<<"{\"v\":";printvec(ex.v);cout<<",\"marked_index\":"<<ex.j<<",\"A_P\":"<<(ex.cost==INF?-1:ex.cost)<<",\"distance\":"<<ex.distance;if(witness&&ex.j>=0){auto w=word(ex);if(w.size()!=size_t(ex.cost))throw runtime_error("witness length mismatch");cout<<",\"word\":\""<<w<<'"';}cout<<'}';}cout<<']';};
 auto printHist=[](const vector<uint64_t>&h){cout<<'{';bool first=true;for(size_t i=0;i<h.size();++i)if(h[i]){if(!first)cout<<',';first=false;cout<<'"'<<i<<"\":"<<h[i];}cout<<'}';};
 cout<<"{\"m\":"<<m<<",\"r\":"<<r<<",\"n\":"<<n<<",\"small_states\":"<<g.count<<",\"visible_states\":"<<visible<<",\"P\":"<<P<<",\"bound\":"<<bound<<",\"max_A_P\":"<<maxA<<",\"missing\":"<<missing<<",\"excess\":"<<excess<<",\"full_radius\":"<<fullRadius<<",\"max_lift_gap\":"<<maxGap<<",\"estimated_bytes\":"<<estimate<<",\"histogram\":";printHist(hist);cout<<",\"gap_histogram\":";printHist(gapHist);cout<<",\"max_examples\":";printExamples(examples);cout<<",\"violations\":";printExamples(violations);
 cout<<",\"elapsed_seconds\":"<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<"}\n";
 }catch(exception&e){cerr<<"ERROR: "<<e.what()<<'\n';return 1;}}
