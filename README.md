# dbbench tools

Python scripts for interacting with dbbench. 

```
$ pip install git+http://vinyl.memsql.com:5000/engineering/dbbench-tools.git
$ autopoc --database=odin --concurrency=1,2 --output=/tmp/out.svg workload.ini
INFO:Running at concurrency level 1 for 10 seconds
INFO:Finished run: avg latency=116.785ms, tps=8
INFO:Running at concurrency level 2 for 10 seconds
INFO:Finished run: avg latency=142.240ms, tps=14
```