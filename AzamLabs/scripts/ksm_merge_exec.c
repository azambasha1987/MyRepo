/*
 * AzamLabs KSM Process Wrapper (ksm_merge_exec.c)
 *
 * Sets prctl(PR_SET_MEMORY_MERGE, 1) before execvp().
 * Marks all anonymous memory pages for this process and any child processes
 * spawned across fork()/execve() as mergeable for the Linux Kernel Samepage Merging (KSM) subsystem.
 *
 * Usage:
 *   /opt/unetlab/wrappers/ksm_merge_exec <executable> [args...]
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/prctl.h>

#ifndef PR_SET_MEMORY_MERGE
#define PR_SET_MEMORY_MERGE 67
#endif

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <command> [args...]\n", argv[0]);
        return 1;
    }

    /* Instruct Linux kernel (6.4+) to treat all anonymous memory pages as KSM-mergeable */
    prctl(PR_SET_MEMORY_MERGE, 1, 0, 0, 0);

    /* Execute the wrapped command with all arguments intact */
    execvp(argv[1], &argv[1]);

    /* If execvp returns, an error occurred */
    perror("execvp failed");
    return 127;
}
