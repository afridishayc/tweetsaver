from google.appengine.ext import ndb

class Tweet(ndb.Model):
    '''Twitter model'''
    user = ndb.StringProperty(indexed = False)
    tweet_text = ndb.StringProperty(indexed = False)
    tweet_tag = ndb.StringProperty()
    dis_pic = ndb.StringProperty(indexed = False)
    timestamp = ndb.DateTimeProperty()