#author: Rishabh Jain
#DATE: 2 MARCH 2019 
#SOURCES: Twitter COOKBOOK, MULTIPLE WEBSITES FOR REFERNCES and, Doubts Clarification from Proffesor and friends in class.
import twitter

def oauth_login():
    # XXX: Go to http://twitter.com/apps/new to create an app and get values
    # for these credentials that you'll need to provide in place of these
    # empty string values that are defined as placeholders.
    # See https://developer.twitter.com/en/docs/basics/authentication/overview/oauth
    # for more information on Twitter's OAuth implementation.
    
    CONSUMER_KEY = ''
    CONSUMER_SECRET = ''
    OAUTH_TOKEN = ''
    OAUTH_TOKEN_SECRET = ''
    
    auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
                               CONSUMER_KEY, CONSUMER_SECRET)
    
    twitter_api = twitter.Twitter(auth=auth)
    return twitter_api

# Sample usage
twitter_api = oauth_login()    

# Nothing to see by displaying twitter_api except that it's now a
# defined variable

print(twitter_api)

#################### Example 16. Making robust Twitter requests

# In[22]:
import sys
import time
from urllib.error import URLError
from http.client import BadStatusLine
import json
import networkx as nx
import matplotlib.pyplot as plt


def make_twitter_request(twitter_api_func, max_errors=10, *args, **kw): 
    
    # A nested helper function that handles common HTTPErrors. Return an updated
    # value for wait_period if the problem is a 500 level error. Block until the
    # rate limit is reset if it's a rate limiting issue (429 error). Returns None
    # for 401 and 404 errors, which requires special handling by the caller.
    def handle_twitter_http_error(e, wait_period=2, sleep_when_rate_limited=True):
    
        if wait_period > 3600: # Seconds
            print('Too many retries. Quitting.', file=sys.stderr)
            raise e
    
        # See https://developer.twitter.com/en/docs/basics/response-codes
        # for common codes
    
        if e.e.code == 401:
            print('Encountered 401 Error (Not Authorized)', file=sys.stderr)
            return None
        elif e.e.code == 404:
            print('Encountered 404 Error (Not Found)', file=sys.stderr)
            return None
        elif e.e.code == 429: 
            print('Encountered 429 Error (Rate Limit Exceeded)', file=sys.stderr)
            if sleep_when_rate_limited:
                print("Retrying in 15 minutes...ZzZ...", file=sys.stderr)
                sys.stderr.flush()
                time.sleep(60*15 + 5)
                print('...ZzZ...Awake now and trying again.', file=sys.stderr)
                return 2
            else:
                raise e # Caller must handle the rate limiting issue
        elif e.e.code in (500, 502, 503, 504):
            print('Encountered {0} Error. Retrying in {1} seconds'                  .format(e.e.code, wait_period), file=sys.stderr)
            time.sleep(wait_period)
            wait_period *= 1.5
            return wait_period
        else:
            raise e

    # End of nested helper function
    
    wait_period = 2 
    error_count = 0 

    while True:
        try:
            return twitter_api_func(*args, **kw)
        except twitter.api.TwitterHTTPError as e:
            error_count = 0 
            wait_period = handle_twitter_http_error(e, wait_period)
            if wait_period is None:
                return
        except URLError as e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print("URLError encountered. Continuing.", file=sys.stderr)
            if error_count > max_errors:
                print("Too many consecutive errors...bailing out.", file=sys.stderr)
                raise
        except BadStatusLine as e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print("BadStatusLine encountered. Continuing.", file=sys.stderr)
            if error_count > max_errors:
                print("Too many consecutive errors...bailing out.", file=sys.stderr)
                raise

# Sample usage

twitter_api = oauth_login()

# See http://bit.ly/2Gcjfzr for twitter_api.users.lookup

response = make_twitter_request(twitter_api.users.lookup, 
                                screen_name="screenName")

print(json.dumps(response, indent=1))

print("END OF FIRST PART")

################## Example 19. Getting all friends or followers for a user

# In[25]:


from functools import partial
from sys import maxsize as maxint

def get_friends_followers_ids(twitter_api, screen_name=None, user_id=None,
                              friends_limit=maxint, followers_limit=maxint):
    
    # Must have either screen_name or user_id (logical xor)
    assert (screen_name != None) != (user_id != None),     "Must have screen_name or user_id, but not both"
    
    # See http://bit.ly/2GcjKJP and http://bit.ly/2rFz90N for details
    # on API parameters
    
    get_friends_ids = partial(make_twitter_request, twitter_api.friends.ids, 
                              count=5000)
    get_followers_ids = partial(make_twitter_request, twitter_api.followers.ids, 
                                count=5000)

    friends_ids, followers_ids = [], []
    
    for twitter_api_func, limit, ids, label in [
                    [get_friends_ids, friends_limit, friends_ids, "friends"], 
                    [get_followers_ids, followers_limit, followers_ids, "followers"]
                ]:
        
        if limit == 0: continue
        
        cursor = -1
        while cursor != 0:
        
            # Use make_twitter_request via the partially bound callable...
            if screen_name: 
                response = twitter_api_func(screen_name=screen_name, cursor=cursor)
            else: # user_id
                response = twitter_api_func(user_id=user_id, cursor=cursor)

            if response is not None:
                ids += response['ids']
                cursor = response['next_cursor']
        
            print('Fetched {0} total {1} ids for {2}'.format(len(ids),                  label, (user_id or screen_name)),file=sys.stderr)
        
            # XXX: You may want to store data during each iteration to provide an 
            # an additional layer of protection from exceptional circumstances
        
            if len(ids) >= limit or response is None:
                break

    # Do something useful with the IDs, like store them to disk...
    return friends_ids[:friends_limit], followers_ids[:followers_limit]

# Sample usage

twitter_api = oauth_login()

friends_ids, followers_ids = get_friends_followers_ids(twitter_api, 
                                                       screen_name="screenName", 
                                                       friends_limit=10, 
                                                       followers_limit=10)
#print(friends_ids)
#print(followers_ids)


reciprocal_friends = set(friends_ids) & set(followers_ids)
friends_ids, followers_ids = get_friends_followers_ids(twitter_api,
                                                      screen_name=reciprocal_friends,
                                                      friends_limit = 10,
                                                      followers_limit = 10)
print(friends_ids)
print(followers_ids)



# ## Example 17. Resolving user profile information

# In[23]:


def get_user_profile(twitter_api, screen_names=None, user_ids=None):
   
    # Must have either screen_name or user_id (logical xor)
    assert (screen_names != None) != (user_ids != None),     "Must have screen_names or user_ids, but not both"
    
    items_to_info = {}

    items = screen_names or user_ids
    
    while len(items) > 0:

        # Process 100 items at a time per the API specifications for /users/lookup.
        # See http://bit.ly/2Gcjfzr for details.
        
        items_str = ','.join([str(item) for item in items[:100]])
        items = items[100:]

        if screen_names:
            response = make_twitter_request(twitter_api.users.lookup, 
                                            screen_name=items_str)
        else: # user_ids
            response = make_twitter_request(twitter_api.users.lookup, 
                                            user_id=items_str)
    
        for user_info in response:
            if screen_names:
                items_to_info[user_info['screen_name']] = user_info
            else: # user_ids
                items_to_info[user_info['id']] = user_info

    return items_to_info

# Sample usage

twitter_api = oauth_login()


#print(get_user_profile(twitter_api, user_ids=[132373965]))
#MYWORK
#MYEDITEDCRAWLER
# In[28]:



def get_top_followers(twitter_api , user_id):
    id = user_id
    friends_ids, followers_ids = get_friends_followers_ids(twitter_api, 
                                                       user_id=id, 
                                                       friends_limit=420, 
                                                       followers_limit=420)
    reciprocal_friends = set(friends_ids) & set(followers_ids)
    user_info_dict = {}
    follower_count_dict = {}
    top_follower_dict = {}
    top_follower_list = []
    for x in reciprocal_friends:
        json_data = json.dumps(get_user_profile(twitter_api, user_ids=[x]), indent = 1) #Get user info
        user_info_dict = json.loads(json_data) #Store user info
        follower_count_dict[str(x)] = (user_info_dict[str(x)]['followers_count']) #EXTRACT ONLY THE USER ID AND THEIR FOLLOWER COUNT
    #print follower_count_dict prints id with number of followers
    
    length = 0
    if len(follower_count_dict) < 5:
        length = len(follower_count_dict)
    else:
        length = 5

    for _ in range(length):
        max_follower = max(follower_count_dict.keys(), key=(lambda k: follower_count_dict[k])) #TO FIND USER WITH HIGHEST FOLLOWER COUNT
        top_follower_dict[max_follower] = follower_count_dict[max_follower]
        top_follower_list.append(int(max_follower)) #ADDING THAT USER TO A LIST
        del follower_count_dict[max_follower] #REMOVE THAT USER FROM THE DICT SO THE NEXT BIGGEST USER CAN BE ADDED TO THE LIST
    return top_follower_list

screen_name = "edmundyu1001"          #START POINT OF CRAWL 
graph_list = []
response = get_top_followers(twitter_api, screen_name) #GET START USERS TOP 5 FOLLOWERS   
ids = next_queue = response

level = 1
max_level = 3         #MAXIMUM DEPTH OF GRAPH(GIVEN)
while level < max_level:
    level += 1
    (queue, next_queue) = (next_queue, [])
    for id in queue:
        graph_dict = {}
        print( "User ID: ", id)       #PRINT USER ID
        response = get_top_followers(twitter_api, user_id=id)   #GET USERS TOP 5 FOLLOWERS 
        next_queue += response
        print ("Top 5 Friends: ", response, "\n")
        graph_dict[id] = response
        graph_list.append(graph_dict)
        
    ids += next_queue
    
#TO ADD START USER IN THE GRAPH 
start_user = {}
response = get_top_followers(twitter_api, screen_name)
start_user[screen_name] = response
graph_list.insert(0, start_user)    #PUT THEM AT BEGINNING OF GRAPH LIST

print ("Printing Follower Graph")

#CREATING GRAPH        
MG = nx.MultiGraph()
for x in graph_list:    #GRAPH LIST RETURNS A LIST OF DICTIONARIES
    for key,value in x.items(): 
        for y in value:                #LOOP THROUGH THE VALUE LISTS INDIVIDUALLY
            MG.add_edge(key,y)          #CREATE EDGE



nx.draw(MG, with_labels=False)# False to keep labels out of picture
plt.savefig("mygraph.png")
plt.show()

print ("Diameter of Follower Graph is: ", nx.diameter(MG))#DIAMETER CALL
avg_dist = nx.average_shortest_path_length(MG)
print ("Average distance is: ", avg_dist)#AVERAGE DISTANCE CALL

