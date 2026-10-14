/* Two separate children, each loading exactly ONE implementation after fork.
 * The parent never dlopens either library. Synchronous pipes schedule timed
 * API invocations; IPC and result formatting stay outside library timers.
 */
#define _GNU_SOURCE
#define main nc_unused_invocation_main
#include "invocation_worker.c"
#undef main
#include <errno.h>
#include <signal.h>
#include <sched.h>
#include <sys/prctl.h>
#include <sys/wait.h>
#include <unistd.h>

typedef struct {int command,reply;pid_t pid;sample reference;uintptr_t address;} child;
typedef struct {sample reference;uintptr_t address;} ready;

static void transfer(int fd,void *buffer,size_t size,int writing) {
  unsigned char *p=buffer;
  while(size) {
    ssize_t n=writing?write(fd,p,size):read(fd,p,size);
    if(n<0&&errno==EINTR)continue;
    if(n<=0){fprintf(stderr,"worker pipe closed or failed\n");exit(9);}
    p+=n;size-=(size_t)n;
  }
}

static child spawn(const char *library,const char *input_path,int cpu_id) {
  int commands[2],replies[2];pid_t parent=getpid();
  if(pipe(commands)||pipe(replies))exit(9);
  pid_t pid=fork();if(pid<0)exit(9);
  if(!pid) {
    if(prctl(PR_SET_PDEATHSIG,SIGTERM)||getppid()!=parent)_exit(9);
    close(commands[1]);close(replies[0]);
    cpu_set_t set;CPU_ZERO(&set);CPU_SET(cpu_id,&set);
    if(sched_setaffinity(0,sizeof(set),&set))_exit(9);
    void *handle=dlopen(library,RTLD_NOW|RTLD_LOCAL);if(!handle)_exit(8);
    entry_fn entry=(entry_fn)dlsym(handle,"nc_benchmark_main");if(!entry)_exit(8);
    char *args[]={"persistent_worker",(char *)input_path,"1",NULL};
    sample reference=measure(entry,3,args);
    for(int i=0;i<2;i++){sample warm={0};accumulate(&warm,measure(entry,3,args),reference);}
    ready r={reference,(uintptr_t)entry};transfer(replies[1],&r,sizeof(r),1);
    for(;;) {
      long repetitions;transfer(commands[0],&repetitions,sizeof(repetitions),0);
      if(!repetitions)break;
      if(repetitions<1||repetitions>100000)_exit(2);
      sample total={0};
      for(long i=0;i<repetitions;i++)accumulate(&total,measure(entry,3,args),reference);
      transfer(replies[1],&total,sizeof(total),1);
    }
    dlclose(handle);close(commands[0]);close(replies[1]);_exit(0);
  }
  close(commands[0]);close(replies[1]);ready r;
  transfer(replies[0],&r,sizeof(r),0);
  return (child){commands[1],replies[0],pid,r.reference,r.address};
}

static sample request(child c,long repetitions) {
  sample result;transfer(c.command,&repetitions,sizeof(repetitions),1);
  transfer(c.reply,&result,sizeof(result),0);return result;
}

static void finish(child c) {
  long zero=0;transfer(c.command,&zero,sizeof(zero),1);
  close(c.command);close(c.reply);int status;
  if(waitpid(c.pid,&status,0)!=c.pid||!WIFEXITED(status)||WEXITSTATUS(status))exit(9);
}

int main(int argc,char **argv) {
  if(argc!=9)return 2;
  long repetitions=number(argv[4],100000),pairs=number(argv[5],256);
  if(strcmp(argv[6],"0")&&strcmp(argv[6],"1"))return 2;
  int first=atoi(argv[6]);char *tail;long cpu_id=strtol(argv[7],&tail,10);
  if(*tail||cpu_id<0||cpu_id>=CPU_SETSIZE)return 2;
  int micro=!strcmp(argv[8],"micro");
  if(!micro&&strcmp(argv[8],"batch"))return 2;
  alarm(300);
  child left=spawn(argv[1],argv[3],(int)cpu_id),right=spawn(argv[2],argv[3],(int)cpu_id);
  if(left.reference.hash!=right.reference.hash||left.reference.values!=right.reference.values)return 6;
  double *trace=calloc((size_t)repetitions*4,sizeof(double));if(!trace)return 9;
  printf("{\"granularity\":\"isolated_%s\",\"repetitions\":%ld,\"pairs\":%ld,\"first\":%s,"
         "\"warmups_per_child\":3,\"left_pid\":%ld,\"right_pid\":%ld,"
         "\"left_entry_address\":\"%llx\",\"right_entry_address\":\"%llx\",\"samples\":[",
         micro?"micro":"batch",repetitions,pairs,first?"true":"false",(long)left.pid,(long)right.pid,
         (unsigned long long)left.address,(unsigned long long)right.address);
  for(long p=0;p<pairs;p++) {
    sample a={0},b={0};long left_first_count=0,steps=micro?repetitions:1;
    for(long i=0;i<steps;i++) {
      int start=(((p+i)%2)==0)==first;sample x,y;left_first_count+=start*(micro?1:repetitions);
      if(start){x=request(left,micro?1:repetitions);y=request(right,micro?1:repetitions);}
      else{y=request(right,micro?1:repetitions);x=request(left,micro?1:repetitions);}
      accumulate(&a,x,left.reference);accumulate(&b,y,left.reference);
      trace[4*i]=x.cpu;trace[4*i+1]=x.wall;trace[4*i+2]=y.cpu;trace[4*i+3]=y.wall;
    }
    if(p)printf(",");
    printf("{\"pair\":%ld,\"left_first\":%s,\"left_first_invocations\":%ld,\"right_first_invocations\":%ld,\"left\":",
           p,(((p%2)==0)==first)?"true":"false",left_first_count,repetitions-left_first_count);
    print_sample(a);printf(",\"right\":");print_sample(b);printf(",\"clock_trace\":[");
    for(long i=0;i<steps;i++)printf("%s[%.17g,%.17g,%.17g,%.17g]",i?",":"",trace[4*i],trace[4*i+1],trace[4*i+2],trace[4*i+3]);
    printf("]}");
  }
  printf("]}\n");free(trace);finish(left);finish(right);return 0;
}
