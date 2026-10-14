/* Identical, separately compiled instrumentation for every pass pipeline.
 * Reinitialize each invocation; consume all live-out values after the timer.
 * Hash full numeric values, rather than PolyBench's rounded printed output.
 */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <time.h>

extern int nc_benchmark_main(int, char **);
static struct timespec begin;
static double seconds;
static unsigned starts, stops;
static uint64_t hash;
static unsigned long values;
static int nonfinite;
static double difference(struct timespec a, struct timespec b) {
  return (b.tv_sec-a.tv_sec)+(b.tv_nsec-a.tv_nsec)*1e-9;
}
void polybench_timer_start(void) {
  starts++;
  if(clock_gettime(CLOCK_MONOTONIC, &begin)) exit(4);
}
void polybench_timer_stop(void) {
  struct timespec end;
  if(clock_gettime(CLOCK_MONOTONIC, &end)) exit(4);
  seconds += difference(begin,end); stops++;
}
void polybench_timer_print(void) {}
__attribute__((noinline)) int nc_sink_fprintf(FILE *stream, const char *fmt, ...) {
  (void)stream;
  if(!strchr(fmt, '%')) return 0;
  va_list ap; va_start(ap,fmt);
  uint64_t bits=0;
  if(strchr(fmt,'f')) {
    double value=va_arg(ap,double);
    if(!isfinite(value)) nonfinite=1;
    memcpy(&bits,&value,sizeof(bits));
  } else if(strchr(fmt,'d')) {
    bits=(uint64_t)(int64_t)va_arg(ap,int);
  } else exit(5);
  va_end(ap);
  hash = (hash ^ bits) * UINT64_C(1099511628211); values++;
  return 0;
}
int main(int argc, char **argv) {
  if(argc!=2) return 2;
  char *tail;
  long repetitions=strtol(argv[1],&tail,10);
  if(*tail || repetitions<1 || repetitions>100000) return 2;
  double total=0;
  uint64_t expected=0;
  unsigned long expected_values=0;
  /* Two warmups in each worker are outside the recorded kernel time. */
  for(long i=-2;i<repetitions;i++) {
    hash=UINT64_C(1469598103934665603); values=0; nonfinite=0;
    starts=stops=0; seconds=0;
    if(nc_benchmark_main(argc,argv) || starts!=1 || stops!=1 ||
       seconds<=0 || !values) return 3;
    if(i==-2) {expected=hash; expected_values=values;}
    if(hash!=expected || values!=expected_values) return 6;
    if(nonfinite) return 7;
    if(i>=0) total+=seconds;
  }
  printf("{\"kernel_seconds\":%.17g,\"checksum\":\"%016llx\","
         "\"values\":%lu,\"repetitions\":%ld}\n", total,
         (unsigned long long)expected, expected_values, repetitions);
  return 0;
}
