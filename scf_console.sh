yum install -y gcc python3-devel mysql-devel
pip3 install -r requirements.txt -t .
#pip3 install mysql-connector-python -t .
pip3 install contextvars -t .
pip3 install django-environ -t .
pip3 install django-cors-headers -t .
pip3 install mysqlclient -t .
pip3 install gunicorn -t .
echo '务必注意不要部署函数！'
