"""Authored deterministic C corpus with predeclared algorithm-family splits.

These are small synthetic programs, not third-party real-world benchmarks.
A family (including every seed/size variant) belongs to exactly one split.
Older research reservations are never imported or opened here.
"""
import hashlib
from src.benchmarks.kernels import PRELUDE, KERNELS, SUFFIX

TRAIN_BODIES = {
 'prefix_scan': 'uint32_t a[N];for(unsigned i=0;i<N;i++)a[i]=random_word(&state);for(unsigned k=0;k<iterations;k++){for(unsigned i=1;i<N;i++)a[i]+=a[i-1];checksum+=a[(k*7u)%N];}',
 'binary_search': 'uint32_t a[N];for(unsigned i=0;i<N;i++)a[i]=i*3u;for(unsigned k=0;k<iterations*200u;k++){unsigned l=0,r=N;uint32_t x=random_word(&state)%(N*3u);while(l<r){unsigned m=l+(r-l)/2;if(a[m]<x)l=m+1;else r=m;}checksum+=l;}',
 'gcd': 'for(unsigned k=0;k<iterations*100u;k++){uint32_t a=random_word(&state),b=random_word(&state)|1u;while(b){uint32_t t=a%b;a=b;b=t;}checksum+=a;}',
 'bit_count': 'for(unsigned k=0;k<iterations*100u;k++){uint32_t x=random_word(&state),v=0;while(x){x&=x-1u;v++;}checksum+=v;}',
 'run_length': 'uint32_t a[N];for(unsigned i=0;i<N;i++)a[i]=(random_word(&state)>>27);for(unsigned k=0;k<iterations;k++){unsigned run=1;for(unsigned i=1;i<N;i++){if(a[i]==a[i-1])run++;else{checksum+=((uint64_t)a[i-1]+1)*run;run=1;}}checksum+=((uint64_t)a[N-1]+1)*run;}',
 'partition': 'uint32_t a[N],b[N];for(unsigned i=0;i<N;i++)a[i]=random_word(&state);for(unsigned k=0;k<iterations;k++){unsigned j=0;uint32_t threshold=random_word(&state);for(unsigned i=0;i<N;i++)if(a[i]<threshold)b[j++]=a[i];for(unsigned i=0;i<j;i++)checksum+=b[i];}',
 'transpose': 'uint32_t a[32][32],b[32][32];for(unsigned y=0;y<32;y++)for(unsigned x=0;x<32;x++)a[y][x]=random_word(&state);for(unsigned k=0;k<iterations;k++){for(unsigned y=0;y<32;y++)for(unsigned x=0;x<32;x++)b[x][y]=a[y][x]+k;checksum+=b[k%32][(k*7u)%32];}',
 'convolution': 'uint32_t a[N],b[N];for(unsigned i=0;i<N;i++)a[i]=random_word(&state);for(unsigned k=0;k<iterations;k++){for(unsigned i=2;i<N-2;i++)b[i]=a[i-2]+2u*a[i-1]+3u*a[i]+2u*a[i+1]+a[i+2];for(unsigned i=2;i<N-2;i++)checksum+=b[i];a[k%(N-4)+2]^=k;}',
 'branch_clamp': 'int32_t a[N];for(unsigned i=0;i<N;i++)a[i]=(int32_t)(random_word(&state)&65535u)-32768;for(unsigned k=0;k<iterations;k++)for(unsigned i=0;i<N;i++){int32_t x=a[i];if(x>12000)x=12000;else if(x< -12000)x= -12000;checksum+=(uint32_t)(x+12000);}',
 'minmax': 'uint32_t a[N];for(unsigned i=0;i<N;i++)a[i]=random_word(&state);for(unsigned k=0;k<iterations;k++){uint32_t lo=0xffffffffu,hi=0;for(unsigned i=0;i<N;i++){uint32_t x=a[i]^k;if(x<lo)lo=x;if(x>hi)hi=x;}checksum+=hi-lo;}',
 'dot_product': 'uint32_t a[N],b[N];for(unsigned i=0;i<N;i++){a[i]=random_word(&state);b[i]=random_word(&state);}for(unsigned k=0;k<iterations;k++){uint32_t sum=0;for(unsigned i=0;i<N;i++)sum+=(a[i]+k)*b[i];checksum+=sum;}',
 'radix_bucket': 'uint32_t a[N],b[N],counts[16],offset[16];for(unsigned i=0;i<N;i++)a[i]=random_word(&state);for(unsigned k=0;k<iterations;k++){for(unsigned j=0;j<16;j++)counts[j]=0;for(unsigned i=0;i<N;i++)counts[(a[i]>>(k%8u*4u))&15u]++;unsigned sum=0;for(unsigned j=0;j<16;j++){offset[j]=sum;sum+=counts[j];}for(unsigned i=0;i<N;i++)b[offset[(a[i]>>(k%8u*4u))&15u]++]=a[i];checksum+=b[k%N];}',
 'lcg_stream': 'for(unsigned k=0;k<iterations;k++)for(unsigned i=0;i<N;i++){uint32_t x=random_word(&state);checksum+=(x^(x>>13))*17u;}',
 'complex_product': 'uint32_t ar[N],ai[N],br[N],bi[N];for(unsigned i=0;i<N;i++){ar[i]=random_word(&state);ai[i]=random_word(&state);br[i]=random_word(&state);bi[i]=random_word(&state);}for(unsigned k=0;k<iterations;k++)for(unsigned i=0;i<N;i++){uint32_t r=ar[i]*br[i]-ai[i]*bi[i],v=ar[i]*bi[i]+ai[i]*br[i];checksum+=r^(v+k);}',
 'strided_copy': 'uint32_t a[N],b[N];for(unsigned i=0;i<N;i++)a[i]=random_word(&state);for(unsigned k=0;k<iterations;k++){for(unsigned i=0;i<N;i++)b[i]=a[(i*17u+k)%N];for(unsigned i=0;i<N;i++)checksum+=b[i];}',
 'finite_state': 'uint32_t a[N];for(unsigned i=0;i<N;i++)a[i]=random_word(&state)&3u;for(unsigned k=0;k<iterations;k++){unsigned q=k&3u;for(unsigned i=0;i<N;i++){switch(q){case 0:q=a[i]==0?1:2;break;case 1:q=a[i]==1?3:0;break;case 2:q=a[i]==2?0:3;break;default:q=a[i]==3?2:1;break;}checksum+=q;}}',
}
# Six new algorithm families; none is used by training or model selection.
TEST_BODIES = {
 'crc32': 'for(unsigned k=0;k<iterations;k++){uint32_t crc=~k;for(unsigned i=0;i<N;i++){crc^=random_word(&state)&255u;for(unsigned b=0;b<8;b++)crc=(crc>>1)^((0u-(crc&1u))&0xedb88320u);}checksum+=~crc;}',
 'edit_distance': 'uint32_t a[48],b[48],prev[49],cur[49];for(unsigned i=0;i<48;i++){a[i]=random_word(&state)&7u;b[i]=random_word(&state)&7u;}for(unsigned k=0;k<iterations;k++){for(unsigned j=0;j<=48;j++)prev[j]=j;for(unsigned i=1;i<=48;i++){cur[0]=i;for(unsigned j=1;j<=48;j++){uint32_t x=prev[j]+1,y=cur[j-1]+1,z=prev[j-1]+(a[i-1]!=b[j-1]);cur[j]=x<y?(x<z?x:z):(y<z?y:z);}for(unsigned j=0;j<=48;j++)prev[j]=cur[j];}checksum+=prev[48];a[k%48]^=1u;}',
 'heapsort': 'uint32_t a[N];for(unsigned k=0;k<iterations;k++){for(unsigned i=0;i<N;i++)a[i]=random_word(&state);for(unsigned start=N/2;start>0;){unsigned root=--start;uint32_t v=a[root];while(root*2+1<N){unsigned child=root*2+1;if(child+1<N&&a[child]<a[child+1])child++;if(v>=a[child])break;a[root]=a[child];root=child;}a[root]=v;}for(unsigned end=N-1;end>0;end--){uint32_t v=a[end];a[end]=a[0];unsigned root=0;while(root*2+1<end){unsigned child=root*2+1;if(child+1<end&&a[child]<a[child+1])child++;if(v>=a[child])break;a[root]=a[child];root=child;}a[root]=v;}for(unsigned i=0;i<N;i++)checksum+=(uint64_t)a[i]*(i+1u);}',
 'floyd_warshall': 'uint32_t d[24][24];for(unsigned k=0;k<iterations;k++){for(unsigned y=0;y<24;y++)for(unsigned x=0;x<24;x++)d[y][x]=x==y?0:1u+(random_word(&state)%1000u);for(unsigned m=0;m<24;m++)for(unsigned y=0;y<24;y++)for(unsigned x=0;x<24;x++){uint32_t v=d[y][m]+d[m][x];if(v<d[y][x])d[y][x]=v;}for(unsigned y=0;y<24;y++)for(unsigned x=0;x<24;x++)checksum+=d[y][x];}',
 'integer_sqrt': 'for(unsigned k=0;k<iterations*100u;k++){uint32_t x=random_word(&state),r=0,bit=1u<<30;while(bit>x)bit>>=2;while(bit){if(x>=r+bit){x-=r+bit;r=(r>>1)+bit;}else r>>=1;bit>>=2;}checksum+=r;}',
 'rational_bezier': 'uint32_t p[4];for(unsigned j=0;j<4;j++)p[j]=random_word(&state)&1023u;for(unsigned k=0;k<iterations;k++)for(unsigned t=0;t<64;t++){uint64_t u=64u-t;uint64_t x=u*u*u*p[0]+3u*u*t*p[1]+3u*u*t*t*p[2]+(uint64_t)t*t*t*p[3];checksum+=x>>18;} '
}


def records():
    entries=[]
    for name,body in KERNELS.items():
        entries.append(dict(id='original_'+name,family=name,split='train',source=PRELUDE+body+SUFFIX))
    for split,bodies in [('train',TRAIN_BODIES),('test',TEST_BODIES)]:
        for family,body in bodies.items():
            for variant in range(2):
                prelude=PRELUDE.replace('1234567u',str(1234567+variant*7919)+'u')
                source='#define N '+str(128 if variant==0 else 257)+'\n'+prelude+body+SUFFIX
                entries.append(dict(id=f'{family}_{variant}',family=family,split=split,source=source))
    for entry in entries:
        entry['source_sha256']=hashlib.sha256(entry['source'].encode()).hexdigest()
    return entries


def manifest():
    rows=[{k:v for k,v in r.items() if k!='source'} for r in records()]
    train={r['family'] for r in rows if r['split']=='train'}
    test={r['family'] for r in rows if r['split']=='test'}
    if train & test:raise ValueError('Algorithm families must not cross splits.')
    if len({r['source_sha256'] for r in rows})!=len(rows):raise ValueError('Duplicate program sources.')
    return {'schema':1,'scope':'Authored synthetic family-disjoint split; not independent real-world programs.',
            'programs':rows,'selection_rule':'Freeze model before any test compilation/evaluation; test outcomes cannot select hyperparameters.'}
