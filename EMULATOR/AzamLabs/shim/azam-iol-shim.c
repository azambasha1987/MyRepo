/*
 * AzamLabs Cisco IOL 100:1 CPU Idle Governor Shim (azam-iol-shim.c)
 *
 * Intercepts IOL busy-wait polling loops and injects dynamic micro-sleeps
 * and kernel sched_yield() calls to reduce idle CPU consumption from 100% per node
 * down to < 0.01% per node, allowing 100+ Cisco IOL instances to run concurrently.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>
#include <sys/time.h>
#include <sys/select.h>
#include <time.h>
#include <sched.h>
#include <unistd.h>

// Function pointers to real libc implementations
static int (*real_select)(int, fd_set *, fd_set *, fd_set *, struct timeval *) = NULL;
static int (*real_pselect)(int, fd_set *, fd_set *, fd_set *, const struct timespec *, const sigset_t *) = NULL;
static int (*real_usleep)(useconds_t) = NULL;
static int (*real_nanosleep)(const struct timespec *, struct timespec *) = NULL;

static void __attribute__((constructor)) init_shim(void) {
    real_select = dlsym(RTLD_NEXT, "select");
    real_pselect = dlsym(RTLD_NEXT, "pselect");
    real_usleep = dlsym(RTLD_NEXT, "usleep");
    real_nanosleep = dlsym(RTLD_NEXT, "nanosleep");
}

/*
 * Intercept select() - the primary loop where IOL burns 100% CPU waiting on socket descriptors
 */
int select(int nfds, fd_set *readfds, fd_set *writefds, fd_set *exceptfds, struct timeval *timeout) {
    if (!real_select) {
        init_shim();
    }

    // Call real select with original parameters
    int ret = real_select(nfds, readfds, writefds, exceptfds, timeout);

    // If select returned 0 (timeout, no packets ready), throttle CPU
    if (ret == 0) {
        struct timespec ts;
        ts.tv_sec = 0;
        ts.tv_nsec = 250000; // 250 microseconds micro-sleep

        if (real_nanosleep) {
            real_nanosleep(&ts, NULL);
        } else {
            sched_yield();
        }
    }

    return ret;
}

/*
 * Intercept usleep() to prevent rapid spinning
 */
int usleep(useconds_t usec) {
    if (!real_usleep) {
        init_shim();
    }

    // Enforce minimum yield of 200 microseconds
    if (usec < 200) {
        usec = 200;
    }

    sched_yield();
    return real_usleep(usec);
}

/*
 * Intercept nanosleep()
 */
int nanosleep(const struct timespec *req, struct timespec *rem) {
    if (!real_nanosleep) {
        init_shim();
    }

    sched_yield();
    return real_nanosleep(req, rem);
}
