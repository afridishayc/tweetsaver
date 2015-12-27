import webapp2
import base64
import json
import urllib
import logging
import datetime
from google.appengine.ext import ndb
from google.appengine.api import search
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from datamodel import Tweet

def creds(key,secret):	
    return base64.b64encode(key+':'+secret)
	
key = 'eKmzNk8gpMKAZZ7xvO86GHBqm'	#client key
secret = 'HwsMjGdNMYorCQMH8x8J07iNc0mJwGTBaRlzFkEFzJuqiOU55j'	#client token
atoken = None

class Mother(webapp2.RequestHandler):

    def tweet_getter(self,z):
        '''gets the valid token and fetches tweets from the twitter SEARCH API'''
        global atoken
        if not atoken :
            result = urlfetch.fetch(url='https://api.twitter.com/oauth2/token',
                payload='grant_type=client_credentials',
                method=urlfetch.POST,
                headers={'Content-Type': 'application/x-www-form-urlencoded','Authorization':'Basic '+`creds(key,secret)`})
            if result.status_code == 200:
                atoken = json.loads(result.content)['access_token']
                return self.get_tweets_from_twitter(z)
            else:
                self.write('Error in getting the token, Try agian!')
        else:
            return self.get_tweets_from_twitter(z)
    def get_tweets_from_twitter(self,z):
        resultx = urlfetch.fetch(url='https://api.twitter.com/1.1/search/tweets.json?q='+urllib.quote_plus(z)+'&count=30',
            method=urlfetch.GET,
            headers={'Authorization':'Bearer '+ atoken})
        if resultx.status_code == 200:
            out_dict = json.loads(resultx.content)
            if out_dict['statuses']:
                return out_dict      
            else:
                return {'message':'no tweets'}
        else:
            return {'message':'Try again'}       
    def timestamp(self,time):
        k = time.split(' ')
        date_time = datetime.datetime.strptime(k[5]+'-'+ k[1]+'-'+k[2]+' '+k[3], '%Y-%b-%d %H:%M:%S')
        return date_time	
class MainHandler(Mother):
    def get(self): 
        index = search.Index(name="tweet_index")
        query = search.Query(query_string='')
        try:
            results = index.search(query)
            tags_list = list()
            for tag in results:
                taskqueue.add(url='/module/tweettask', params={'tag': tag.doc_id})				
        except search.Error:
            self.write('search failed')	
        else:
            self.response.set_status(200)
class TweetTask(Mother):
    def post(self):
        tag = self.request.get('tag')
        tweets = self.tweet_getter(tag)
        entity_list = list()		
        for t in tweets['statuses']:
            tweet = Tweet(id = t['id_str'])
            tweet.tweet_text = t['text']    
            tweet.tweet_tag = tag
            tweet.dis_pic = t['user']['profile_image_url']
            tweet.user = t['user']['name']
            tweet.timestamp = self.timestamp(t['created_at'])
            entity_list.append(tweet)
        ndb.put_multi(entity_list)
        logging.info('done')
        self.response.set_status(200)
app = webapp2.WSGIApplication([
    webapp2.Route('/module/add', MainHandler, name='home'),
    webapp2.Route('/module/tweettask', TweetTask, name='tweettask'),
], debug=True)