// Independent literal-list verifier. Does not include the generator code.
#include <algorithm>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using Vec=std::vector<int>;

Vec csv(const std::string& text) {
    Vec values;std::stringstream input(text);std::string item;
    while(std::getline(input,item,',')) {
        size_t used=0;int value=std::stoi(item,&used);
        if(used!=item.size())throw std::runtime_error("Invalid integer");
        values.push_back(value);
    }
    return values;
}

void move(Vec& state,char c) {
    if(c=='L')std::rotate(state.begin(),state.begin()+1,state.end());
    else if(c=='R')std::rotate(state.begin(),state.end()-1,state.end());
    else if(c=='X')std::swap(state[0],state[1]);
    else throw std::runtime_error("Invalid word letter");
}

void verify(const Vec& state,const std::string& word,const Vec& expected) {
    if(state.size()!=17 || expected.size()!=512 || expected[0]!=0)
        throw std::runtime_error("Invalid table dimensions");
    Vec tags=state,named;int zero=0;
    for(size_t j=0;j<state.size();++j) {
        if((state[j]==0)!=(j%2==0))throw std::runtime_error("Invalid zero pattern");
        if(tags[j]==0)tags[j]=-(++zero);else named.push_back(tags[j]);
    }
    std::sort(named.begin(),named.end());
    if(named!=Vec({1,2,3,4,5,6,7,8}))throw std::runtime_error("Invalid named labels");
    for(unsigned mask=1;mask<512;++mask) {
        Vec original=tags,projected;
        auto alive=[&](int x) {return x>0 || (mask & (1u<<(-x-1)));};
        for(int x:original)if(alive(x))projected.push_back(std::max(0,x));
        std::string reduced;
        for(char c:word) {
            bool emit=false;
            if(c=='L')emit=alive(original.front());
            else if(c=='R')emit=alive(original.back());
            else if(c=='X')emit=alive(original[0]) && alive(original[1]);
            else throw std::runtime_error("Invalid word letter");
            move(original,c);
            if(emit) {
                move(projected,c);
                if(!reduced.empty() && ((reduced.back()=='L' && c=='R') || (reduced.back()=='R' && c=='L')))
                    reduced.pop_back();
                else reduced+=c;
            }
        }
        Vec erased;
        for(int x:original)if(alive(x))erased.push_back(std::max(0,x));
        if(projected!=erased)throw std::runtime_error("Projection identity failed");
        for(size_t j=0;j<projected.size();++j)
            if(projected[j]!=(j<8?int(j)+1:0))throw std::runtime_error("Wrong projected goal");
        if(int(reduced.size())!=expected[mask])throw std::runtime_error("Wrong projected word cost");
    }
}

int main() {
    try {
        std::string line;
        while(std::getline(std::cin,line)) {
            const size_t a=line.find('|'),b=line.find('|',a+1);
            if(a==std::string::npos || b==std::string::npos)throw std::runtime_error("Invalid input line");
            verify(csv(line.substr(0,a)),line.substr(a+1,b-a-1),csv(line.substr(b+1)));
            std::cout<<"PASS 511\n"<<std::flush;
        }
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 2;}
}
