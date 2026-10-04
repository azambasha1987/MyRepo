/*
 * AzamLabs KSM Process Wrapper (azambasha-ksm-merge-exec.c)
 * Mirror alias for ksm_merge_exec.c
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

    prctl(PR_SET_MEMORY_MERGE, 1, 0, 0, 0);
    execvp(argv[1], &argv[1]);
    perror("execvp failed");
    return 127;
}
