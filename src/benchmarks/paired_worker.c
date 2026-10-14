/* Persistent paired worker. Both clocks measure the same native kernel;
 * outputs and initialization stay outside timers. No interrupted trial is cut.
 */
#define _POSIX_C_SOURCE 200809L
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <time.h>

typedef int (*entry_fn)(int, char **);
typedef struct { double wall, cpu; uint64_t hash; unsigned long values; } sample;
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
  if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&cpu_start) ||
     clock_gettime(CLOCK_MONOTONIC,&wall_start)) exit(4);
}
void polybench_timer_stop(void) {
  struct timespec w,c;
  if(clock_gettime(CLOCK_MONOTONIC,&w) || clock_gettime(CLOCK_THREAD_CPUTIME_ID,&c)) exit(4);
  wall+=elapsed(wall_start,w); cpu+=elapsed(cpu_start,c); stops++;
}
void polybench_timer_print(void) {}
__attribute__((noinline)) int nc_sink_fprintf(FILE *stream,const char *fmt,...) {
  (void)stream;
  if(!strchr(fmt,'%')) return 0;
  va_list ap; va_start(ap,fmt); uint64_t bits=0;
  if(strchr(fmt,'f')) {
    double value=va_arg(ap,double);
    if(!isfinite(value)) nonfinite=1;
    memcpy(&bits,&value,sizeof(bits));
  } else if(strchr(fmt,'d')) bits=(uint64_t)(int64_t)va_arg(ap,int);
  else exit(5);
  va_end(ap); hash=(hash^bits)*UINT64_C(1099511628211); values++;
  return 0;
}
static sample measure(entry_fn entry,long repetitions,char **argv) {
  sample s={0,0,0,0};
  for(long i=0;i<repetitions;i++) {
    wall=cpu=0; starts=stops=0; values=0; nonfinite=0;
    hash=UINT64_C(1469598103934665603);
    if(entry(1,argv) || starts!=1 || stops!=1 || !values ||
       !isfinite(wall) || !isfinite(cpu) || wall<=0 || cpu<=0) exit(3);
    if(nonfinite) exit(7);
    if(i && (hash!=s.hash || values!=s.values)) exit(6);
    s.hash=hash; s.values=values; s.wall+=wall; s.cpu+=cpu;
  }
  return s;
}
static void print_sample(sample s) {
  printf("{\"wall_seconds\":%.17g,\"cpu_seconds\":%.17g,"
         "\"checksum\":\"%016llx\",\"values\":%lu}",
         s.wall,s.cpu,(unsigned long long)s.hash,s.values);
}
static long number(const char *s,long limit) {
  char *tail; long n=strtol(s,&tail,10);
  if(*tail || n<1 || n>limit) exit(2);
  return n;
}
int main(int argc,char **argv) {
  if(argc!=6) return 2;
  long repetitions=number(argv[3],100000),pairs=number(argv[4],256);
  if(strcmp(argv[5],"0") && strcmp(argv[5],"1")) return 2;
  int first=atoi(argv[5]);
  void *left_handle=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
  void *right_handle=dlopen(argv[2],RTLD_NOW|RTLD_LOCAL);
  if(!left_handle || !right_handle) {fprintf(stderr,"%s\n",dlerror()); return 8;}
  entry_fn left=(entry_fn)dlsym(left_handle,"nc_benchmark_main");
  entry_fn right=(entry_fn)dlsym(right_handle,"nc_benchmark_main");
  if(!left || !right) return 8;
  sample reference=measure(left,1,argv);
  for(int i=0;i<2;i++) {
    sample a=measure(left,1,argv),b=measure(right,1,argv);
    if(a.hash!=reference.hash || b.hash!=reference.hash ||
       a.values!=reference.values || b.values!=reference.values) return 6;
  }
  printf("{\"repetitions\":%ld,\"pairs\":%ld,\"first\":%s,\"samples\":[",
         repetitions,pairs,first?"true":"false");
  for(long p=0;p<pairs;p++) {
    int left_first=((p%2)==0)==first;
    sample a,b;
    if(left_first) {a=measure(left,repetitions,argv); b=measure(right,repetitions,argv);}
    else {b=measure(right,repetitions,argv); a=measure(left,repetitions,argv);}
    if(a.hash!=reference.hash || b.hash!=reference.hash ||
       a.values!=reference.values || b.values!=reference.values) return 6;
    if(p) printf(",");
    printf("{\"pair\":%ld,\"left_first\":%s,\"left\":",p,left_first?"true":"false");
    print_sample(a); printf(",\"right\":"); print_sample(b); printf("}");
  }
  printf("]}\n"); dlclose(left_handle); dlclose(right_handle); return 0;
}
