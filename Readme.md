<!-- dx-header -->
# fusetester (DNAnexus Platform App)

Testing 'mounting' of file(s) using FUSE

This is the source code for an app that runs on the DNAnexus Platform.
For more information about how to run or modify it, see
https://wiki.dnanexus.com/.
<!-- /dx-header -->

You may just want to look at ``resources/opt/lldxfuse.py`` as an example
of interacting with DNAnexus using fuse. This script could also be run
on a local computer (provided you have python-llfuse and the DNAnexus
SDK installed) to allow files on DNAnexus to appear to be local. This might
be useful for visualization using your favorite genome browser.

I have not really looked into optimizing the number of threads or buffer size,
that is left as an exercise to the reader...

This test applet does not do much-- it just loops through each provided BAM
file and calls ``samtools`` to determine how many reads from chromosome 22
are in each file. Since the index is used, it does not have to read the
whole file!

## Inputs

* **Input BAM files** ``bamfiles``: ``array:file``
* **Indices for BAM files** ``baifiles``: ``array:file``
> the corresponding ``bamfiles`` and ``baifiles`` have to be provided
> in the same order

## Outputs

* There are no outputs-- look at the log. If everything worked, the number
  of reads for each bamfile from chromosome 22 will be reported.
