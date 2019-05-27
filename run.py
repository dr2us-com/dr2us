from albumy import *
app = create_app()
if __name__ == '__main__':	
	app.run(debug=True, threaded=True,host='0.0.0.0',port=80,ssl_context=('pem/cert.pem', 'pem/key.pem'))