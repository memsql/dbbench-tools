# dbbench tools

Python scripts for improving `dbbench` workflows. 

## Using `dbbench-tools`:

```
$ dbbench-scale-test --database=odin --concurrency=1,2 --output=/tmp/out.svg workload.ini
INFO:Running at concurrency level 1 for 10 seconds
INFO:Finished run: avg latency=116.785ms, tps=8
INFO:Running at concurrency level 2 for 10 seconds
INFO:Finished run: avg latency=142.240ms, tps=14
```

## Installing `dbbench-tools`

### Simple install on Ubuntu:

 - `sudo apt-get install python-pip python-numpy python-scipy python-dev pkg-config libxft-dev build-essential`
 - `sudo pip install git+https://github.com/memsql/dbbench-tools.git`
 - Install [`dbbench`](https://github.com/memsql/dbbench)

### Install elsewhere:

To install `dbbench-tools`, you must first install `pip` and the `numpy`
python package.

#### `pip`

You can install `pip` via one of the following:

 - `sudo apt-get install python-pip`
 - `sudo easy_install pip`

#### `numpy`

You can install `numpy` via one of the following:
 - `sudo apt-get install python-numpy`
 - `sudo pip install numpy`
 - Directly the scipy website: http://www.scipy.org/scipylib/download.html

#### `matplotlib`

`dbbench-tools` depends on a python package for generating charts, `matplotlib`. It requires serveral dependencies to install. You can get these via:

 - `sudo apt-get install python-dev pkg-config libxft-dev build-essential`

#### `scipy`

`dbbench-tools` depends on a python package for performing statistical tests, `scipy`.
It requires several dependencies to install. You can get these via:

 - `sudo apt-get install libblas-dev liblapack-dev gfortran`

It might be easier to just install scipy directly, e.g. via:

 - `sudo apt-get install python-scipy`

#### `dbbench-tools`

Then you can install `dbbench-tools` using `pip`:

 - `sudo pip install git+https://github.com/memsql/dbbench-tools.git`
