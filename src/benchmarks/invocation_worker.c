/* Alternate after EACH invocation, retaining both clocks and every output.
 * This is a new protocol; the previous batch worker remains immutable. */
#define _POSIX_C_SOURCE 200809L
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <time.h>

typedef int (*entry_fn)(int,char **);
typedef struct {double wall,cpu;uint64_t hash;unsigned long values;} sample;
static struct timespec wall_start,cpu_start;
static double wall,cpu;
static uint64_t hash;
static unsigned long values;
static unsigned starts,stops;
static int nonfinite;
static double elapsed(struct timespec a,struct timespec b) {
  return (b.tv_sec-a.tv_sec)+(b.tv_nsec-a.tv_nsec)*1e-9;
}
void polybench_timer_start(void) {
  starts++;
  if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&cpu_start)||clock_gettime(CLOCK_MONOTONIC,&wall_start))exit(4);
}
void polybench_timer_stop(void) {
  struct timespec w,c;
  if(clock_gettime(CLOCK_MONOTONIC,&w)||clock_gettime(CLOCK_THREAD_CPUTIME_ID,&c))exit(4);
  wall+=elapsed(wall_start,w);cpu+=elapsed(cpu_start,c);stops++;
}
void polybench_timer_print(void) {}
void nc_emit_u64(uint64_t value) {
  hash=(hash^value)*UINT64_C(1099511628211);values++;
}
__attribute__((noinline)) int nc_sink_fprintf(FILE *stream,const char *fmt,...) {
  (void)stream;if(!strchr(fmt,'%'))return 0;
  va_list ap;va_start(ap,fmt);uint64_t bits=0;
  if(strchr(fmt,'f')) {
    double value=va_arg(ap,double);if(!isfinite(value))nonfinite=1;
    memcpy(&bits,&value,sizeof(bits));
  } else if(strchr(fmt,'d'))bits=(uint64_t)(int64_t)va_arg(ap,int);
  else exit(5);
  va_end(ap);nc_emit_u64(bits);return 0;
}
static sample measure(entry_fn entry,int argc,char **argv) {
  wall=cpu=0;starts=stops=0;values=0;nonfinite=0;
  hash=UINT64_C(1469598103934665603);
  if(entry(argc,argv)||starts!=1||stops!=1||!values||
     !isfinite(wall)||!isfinite(cpu)||wall<=0||cpu<=0)exit(3);
  if(nonfinite)exit(7);
  return (sample){wall,cpu,hash,values};
}
static void accumulate(sample *total,sample s,sample reference) {
  if(s.hash!=reference.hash||s.values!=reference.values)exit(6);
  total->wall+=s.wall;total->cpu+=s.cpu;total->hash=s.hash;total->values=s.values;
}
static void print_sample(sample s) {
  printf("{\"wall_seconds\":%.17g,\"cpu_seconds\":%.17g,\"checksum\":\"%016llx\",\"values\":%lu}",
         s.wall,s.cpu,(unsigned long long)s.hash,s.values);
}
static long number(const char *s,long limit) {
  char *tail;long n=strtol(s,&tail,10);if(*tail||n<1||n>limit)exit(2);return n;
}
int main(int argc,char **argv) {
  if(argc!=6&&argc!=7)return 2;
  long repetitions=number(argv[3],100000),pairs=number(argv[4],256);
  if(strcmp(argv[5],"0")&&strcmp(argv[5],"1"))return 2;
  int first=atoi(argv[5]);
  char *entry_argv[]={argv[0],argc==7?argv[6]:NULL,"1",NULL};
  int entry_argc=argc==7?3:1;
  void *lh=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL),*rh=dlopen(argv[2],RTLD_NOW|RTLD_LOCAL);
  if(!lh||!rh){fprintf(stderr,"%s\n",dlerror());return 8;}
  entry_fn left=(entry_fn)dlsym(lh,"nc_benchmark_main"),right=(entry_fn)dlsym(rh,"nc_benchmark_main");
  if(!left||!right)return 8;
  sample reference=measure(left,entry_argc,entry_argv);
  for(int i=0;i<2;i++) {
    sample a={0},b={0};
    accumulate(&a,measure(left,entry_argc,entry_argv),reference);
    accumulate(&b,measure(right,entry_argc,entry_argv),reference);
  }
  printf("{\"granularity\":\"one_invocation\",\"repetitions\":%ld,\"pairs\":%ld,\"first\":%s,"
         "\"left_entry_address\":\"%llx\",\"right_entry_address\":\"%llx\",\"samples\":[",
         repetitions,pairs,first?"true":"false",(unsigned long long)(uintptr_t)left,
         (unsigned long long)(uintptr_t)right);
  for(long p=0;p<pairs;p++) {
    sample a={0},b={0};long left_first_count=0;
    for(long i=0;i<repetitions;i++) {
      int left_first=((p+i)%2==0)==first;left_first_count+=left_first;
      if(left_first) {
        accumulate(&a,measure(left,entry_argc,entry_argv),reference);
        accumulate(&b,measure(right,entry_argc,entry_argv),reference);
      } else {
        accumulate(&b,measure(right,entry_argc,entry_argv),reference);
        accumulate(&a,measure(left,entry_argc,entry_argv),reference);
      }
    }
    if(p)printf(",");
    printf("{\"pair\":%ld,\"left_first\":%s,\"left_first_invocations\":%ld,\"right_first_invocations\":%ld,\"left\":",
           p,(((p%2)==0)==first)?"true":"false",left_first_count,repetitions-left_first_count);
    print_sample(a);printf(",\"right\":");print_sample(b);printf("}");
  }
  printf("]}\n");dlclose(lh);dlclose(rh);return 0;
}
