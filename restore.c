#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <sys/stat.h>

int main(void) {
    // rm new chunks
    remove("folder1/chunk_3");
    remove("folder2/chunk_1");
    remove("folder3/chunk_2");

    // write original contents to txt files
    remove("folder1/local_chunks.txt");
    int fd = open("folder1/local_chunks.txt", O_CREAT | O_RDWR);
    char txt1[] = "1,chunk_1\n2,chunk_2\n3,LASTCHUNK";
    write(fd, txt1, strlen(txt1));
    close(fd);
    chmod("folder1/local_chunks.txt", 0xffff);

    remove("folder2/local_chunks.txt");
    fd = open("folder2/local_chunks.txt", O_CREAT | O_RDWR);
    char txt2[] = "2,chunk_2\n3,chunk_3\n3,LASTCHUNK";
    write(fd, txt2, strlen(txt2));
    close(fd);
    chmod("folder2/local_chunks.txt", 0xffff);

    remove("folder3/local_chunks.txt");
    fd = open("folder3/local_chunks.txt", O_CREAT | O_RDWR);
    char txt3[] = "1,chunk_1\n3,chunk_3\n3,LASTCHUNK";
    write(fd, txt3, strlen(txt3));
    close(fd);
    chmod("folder3/local_chunks.txt", 0xffff);
    return 0;
}