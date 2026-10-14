/* Secondary confirmation: one implementation resident per worker process. */
#define main nc_unused_invocation_main
#include "invocation_worker.c"
#undef main

int main(int argc,char **argv) {
  if(argc!=4)return 2;
  long repetitions=number(argv[3],100000);
  void *handle=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
  if(!handle)return 8;
  entry_fn entry=(entry_fn)dlsym(handle,"nc_benchmark_main");if(!entry)return 8;
  char *args[]={argv[0],argv[2],"1",NULL};
  sample reference=measure(entry,3,args),total={0};
  for(int i=0;i<2;i++){sample warm={0};accumulate(&warm,measure(entry,3,args),reference);}
  for(long i=0;i<repetitions;i++)accumulate(&total,measure(entry,3,args),reference);
  printf("{\"mode\":\"one_implementation\",\"repetitions\":%ld,\"sample\":",repetitions);
  print_sample(total);printf("}\n");dlclose(handle);return 0;
}
