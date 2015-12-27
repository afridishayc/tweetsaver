#!/usr/bin/env python
#tweetinside
import os
import urllib
import base64
import webapp2
import json
import jinja2
import logging
import datetime
from google.appengine.ext import ndb
from google.appengine.api import search
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from datamodel import Tweet
template_dir = os.path.join(os.path.dirname(__file__), 'templates')	
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(template_dir),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
	
def creds(key,secret):		#base64 encoder for client key and secret
    return base64.b64encode(key+':'+secret)
	
key = 'eKmzNk8gpMKAZZ7xvO86GHBqm'	#client key
secret = 'HwsMjGdNMYorCQMH8x8J07iNc0mJwGTBaRlzFkEFzJuqiOU55j'	#client token
atoken = None
class Check(ndb.Model):
    date = ndb.DateTimeProperty()
class Father(webapp2.RequestHandler):	#superclass
    def write(self,text):
        '''printing out the text'''
        self.response.write(text)
    def show(self,name,temp_params=None):
        '''template rendering'''
        template = JINJA_ENVIRONMENT.get_template(name)
        if temp_params:
            self.response.write(template.render(temp_params))
        else:
            self.response.write(template.render({}))
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
        resultx = urlfetch.fetch(url='https://api.twitter.com/1.1/search/tweets.json?q='+urllib.quote_plus(z)+'&count=10',
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
class MainHandler(Father):
    def get(self):
        index = search.Index(name="tweet_index")
        query = search.Query(query_string='')
        try:
            results = index.search(query)
            tags_dict = dict()
            for tag in results:
                logging.info(tag.fields[0].value)
                tags_dict[tag.fields[0].value] =  self.uri_for('gettweets',tag=tag.fields[0].value, _full=True)
        except search.Error:
            self.write('search failed')		
        else:
            self.show('tweets.html',{'tags':tags_dict})
    def post(self):
        z = self.request.get('qvar') 
        index = search.Index(name="tweet_index")
        query_string = 'tag:'+ z
        query_options = search.QueryOptions(ids_only = True)
        query = search.Query(query_string=query_string, options=query_options)
        try:
            results = index.search(query)
            if results.number_found > 0:
                for tweet_document in results:
                    tag = tweet_document.doc_id
                    break
                tweets = Tweet.query(Tweet.tweet_tag == tag).order(-Tweet.timestamp).fetch_page(30)
                out_list = list()
                for tweet in tweets[0]:
                    out_dict = dict()
                    out_dict['name'] = tweet.user
                    out_dict['text'] = tweet.tweet_text
                    out_dict['propic'] = tweet.dis_pic
                    out_dict['timestamp'] = tweet.timestamp + datetime.timedelta(hours = 5,minutes=30)
                    out_list.append(out_dict)	
                self.show('ourtweets.html',{'tweets':out_list,'tag':z,'next_url':self.uri_for('next',qfor=z,next=tweets[1].urlsafe(), _full=True),'next':tweets[2],'prev':False})				
            else:
                tweets = self.tweet_getter(z)
                tweets.update({'tag':z})
                self.show('tweets.html',tweets)
                #self.write(tweets)
                if not tweets.get('message'):
                    taskqueue.add(url='/tasks/tweetadder', params={'tweets':json.dumps(tweets['statuses']),'tag':z,'meta':tweets['search_metadata']['query']})
                    pass
        except search.Error:
            self.write('search failed')

class GetTweets(Father):
    def get(self):
        z = self.request.get('tag') 
        index = search.Index(name="tweet_index")
        query_string = 'tag:'+ z
        query = search.Query(query_string=query_string)
        try:
            results = index.search(query)
            if results.number_found > 0:
                for tweet_document in results:
                    tag = tweet_document.doc_id
                    break
                tweets = Tweet.query(Tweet.tweet_tag == tag).order(-Tweet.timestamp).fetch_page(30)
                out_list = list()
                for tweet in tweets[0]:
                    out_dict = dict()
                    out_dict['name'] = tweet.user
                    out_dict['text'] = tweet.tweet_text
                    out_dict['propic'] = tweet.dis_pic
                    out_dict['timestamp'] = tweet.timestamp + datetime.timedelta(hours = 5,minutes=30)
                    out_list.append(out_dict)	
                self.show('ourtweets.html',{'tweets':out_list,'tag':z,'next_url':self.uri_for('next',qfor=z,curs=tweets[1].urlsafe(),type='next', _full=True),'next':tweets[2],'prev':False})	
            else:
                self.write('No tweets')
        except search.Error:
            self.write('search failed')

class Next(Father):
    def get(self):
        
        curs = ndb.Cursor(urlsafe = self.request.get('curs'))
        qfor = self.request.get('qfor')
        forw = Tweet.query(Tweet.tweet_tag == qfor).order(-Tweet.timestamp).fetch_page(30,start_cursor = curs)
        rev = Tweet.query(Tweet.tweet_tag == qfor).order(Tweet.timestamp).fetch_page(30,start_cursor = curs)
        next = forw[2]
        prev = rev[2]
        if self.request.get('type') == 'next':
            tweets = forw
        else:
            tweets = rev
        out_list = list()
        for tweet in tweets[0]:
            out_dict = dict()
            out_dict['name'] = tweet.user
            out_dict['text'] = tweet.tweet_text
            out_dict['propic'] = tweet.dis_pic
            out_dict['timestamp'] = tweet.timestamp + datetime.timedelta(hours = 5,minutes=30)
            out_list.append(out_dict)	
        if forw[1]:
            curs1=forw[1].urlsafe()
        elif rev[1]:
            curs1 = rev[1].urlsafe()
        else:
            curs1 = ''
        #self.write(forw[1].urlsafe())
        
        #self.write(rev[1].urlsafe())
        self.show('ourtweets.html',{'tweets':out_list,'tag':qfor,'next_url':self.uri_for('next',qfor=qfor,curs=curs1,type='next', _full=True),'prev_url':self.uri_for('next',curs=curs1,qfor=qfor,type='prev', _full=True),'next':next,'prev':prev})
        
class TweetAdder(Father):
        def post(self):
            
            tag = self.request.get('tag')
            logging.info(tweets)
            ###add to the datastore
            meta = self.request.get('meta')
            tweet_document = search.Document(doc_id=meta ,fields=[search.TextField(name='tag',value=tag.encode('utf-8'))])
            try:
                index = search.Index(name="tweet_index")
                index.put(tweet_document)
            except search.Error:
                logging.exception('index put failed')
            else:
                entity_list = list()
                for t in tweets:
                    tweet = Tweet(id = t['id_str'])
                    tweet.tweet_text = t['text']    
                    tweet.tweet_tag = meta
                    tweet.dis_pic = t['user']['profile_image_url']
                    tweet.user = t['user']['name']
                    tweet.timestamp = self.timestamp(t['created_at'])
                    entity_list.append(tweet)
                ndb.put_multi(entity_list)	
                logging.info('entities insertion success')
                self.response.set_status(200)
class Testy(Father):
    def get(self):
        self.show("youtube.html")          
app = webapp2.WSGIApplication([
    webapp2.Route('/', MainHandler, name='home'),
    webapp2.Route('/next',Next, name='next'),
    webapp2.Route('/gettweets',GetTweets, name='gettweets'),
    webapp2.Route('/tasks/tweetadder',TweetAdder, name='tweetadder'),
    webapp2.Route('/test',Testy, name='testy'),
], debug=True)
