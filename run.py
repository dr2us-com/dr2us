from flask import Response,request
from albumy import *
app = create_app()
# @app.before_request
# def before_request():
#     if request.url.startswith('http://'):
#         return redirect(request.url.replace('http://', 'https://'), code=301)
        
@app.route('/.well-known/acme-challenge/<challenge>')
def letsencrypt_check(challenge):
    challenge_response = {
        "<challenge_token>":"<challenge_response>",
        "<challenge_token>":"<challenge_response>"
    }
    return Response(challenge_response[challenge], mimetype='text/plain')
if __name__ == '__main__':
        app.run(debug=True, threaded=True,host='0.0.0.0',port=80)
        # app.run(debug=True, threaded=True,host='0.0.0.0',port=443,
        #                         ssl_context=('/etc/letsencrypt/live/dr2us.com/fullchain.pem',
        #                                         '/etc/letsencrypt/live/dr2us.com/privkey.pem'))
        #app.run(debug=True, threaded=True,host='0.0.0.0',port=443,ssl_context=('pem/cert.pem', 'pem/key.pem'))
