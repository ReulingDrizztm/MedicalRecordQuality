#! /bin/bash
#python3 manage.py makemigrations MedicalQuality
#python3 manage.py migrate
SERVER_PATH=`pwd`
cd $SERVER_PATH
cd script
myfile=$SERVER_PATH"/script/uwsgi.pid"

start(){
if [ -a "$myfile" ]
then
uwsgi --stop uwsgi.pid
sleep 1.5
echo "">uwsgi.log
uwsgi --ini uwsgi.ini
sleep 1.5
s=`cat uwsgi.pid`
echo "process PID is [$s]"
else
echo "">uwsgi.log
uwsgi --ini uwsgi.ini
sleep 1.5
s=$(cat uwsgi.pid)
echo "process PID is [$s]"
fi
}

stop(){
if [ -a "$myfile" ]
then
uwsgi --stop uwsgi.pid
else
echo "no process uwsgi"
fi

}

restart(){
echo "">uwsgi.log
uwsgi --reload uwsgi.pid
}

case "$1" in
  start)
    echo "process is starting..."
    start
    ;;
  stop)
    stop
    sleep 1.5s
    ;;
  restart)
    stop
    sleep 1.5s
    start
    ;;
  *)
    exit 1
    ;;
esac
ps -ef --sort=+start|grep "$USER"|grep uwsgi
exit 0