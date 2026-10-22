/* Native process timer: excludes Python launch/setup from measured clocks.
 * Trusted local programs only; limits do not provide a security sandbox. */
#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sched.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static double seconds(struct timespec t) {
    return (double)t.tv_sec + (double)t.tv_nsec / 1e9;
}
static int limit(int which, rlim_t value) {
    struct rlimit bound = {value, value};
    return setrlimit(which, &bound);
}
int main(int argc, char **argv) {
    if (argc < 3) return 120;
    char *end;
    long descriptor = strtol(argv[1], &end, 10);
    if (*end || descriptor < 3 || descriptor > 1024) return 120;
    int fd = (int)descriptor;
    cpu_set_t allowed, chosen;
    if (sched_getaffinity(0, sizeof allowed, &allowed)) return 121;
    int cpu = -1;
    for (int i = 0; i < CPU_SETSIZE; ++i)
        if (CPU_ISSET(i, &allowed)) { cpu = i; break; }
    if (cpu < 0) return 121;
    CPU_ZERO(&chosen); CPU_SET(cpu, &chosen);
    if (sched_setaffinity(0, sizeof chosen, &chosen)) return 121;
    struct timespec begin, finish;
    if (clock_gettime(CLOCK_MONOTONIC, &begin)) return 122;
    pid_t parent = getpid(), child = fork();
    if (child < 0) return 123;
    if (child == 0) {
        /* A timeout/cancel of the launcher must not leave its child running. */
        if (prctl(PR_SET_PDEATHSIG, SIGKILL) || getppid() != parent) _exit(124);
        close(fd);
        if (limit(RLIMIT_CPU, 3) || limit(RLIMIT_AS, 768UL*1024*1024)
            || limit(RLIMIT_FSIZE, 65536) || limit(RLIMIT_CORE, 0)
            || limit(RLIMIT_NOFILE, 32)) _exit(125);
        execv(argv[2], &argv[2]);
        _exit(126);
    }
    int status;
    struct rusage usage;
    pid_t waited;
    do { waited = wait4(child, &status, 0, &usage); } while (waited < 0 && errno == EINTR);
    if (waited != child || clock_gettime(CLOCK_MONOTONIC, &finish)) return 127;
    double cpu_seconds = usage.ru_utime.tv_sec + usage.ru_utime.tv_usec / 1e6
        + usage.ru_stime.tv_sec + usage.ru_stime.tv_usec / 1e6;
    int code = WIFEXITED(status) ? WEXITSTATUS(status) : -WTERMSIG(status);
    if (dprintf(fd, "{\"cpu\":%.9f,\"wall\":%.9f,\"exit_code\":%d,\"cpu_id\":%d}\n",
                cpu_seconds, seconds(finish)-seconds(begin), code, cpu) < 0) return 128;
    return 0;
}
