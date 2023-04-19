# youtube-burst


This project uses code scripts to simulate YouTube users. These scripts detail the behavior of a given simulated user. Many of these "sock puppets" are run in parallel in the cloud, which is detailed a separate [project](https://github.com/carleski/ytburst-terraform), with the help of Rob Carleski. Together, these sock puppet scripts serve as the data collection portion of a paper on YouTube user agency and ability to contest bad recommendations. It is currently under review at ICWSM. 

![Alt text](./figures/AIN_analysis.png)

## Description

Can YouTube users effectively remove unwanted recommendations? We simulated users of a variety of interests and disinterests to answer this question. Broadly, these sock puppets first purposely populate their feed with videos from this unwanted topic ("stain phase"); Then, they take on one of a variety of strategies to try to eliminate such videos from being recommended ("scrub phase"). These strategies correspond to different features on YouTube that one could use to indicate disinterest towards certain videos, such as the "Not Interested" button, the "Dislike" button, and the "Delete from watch history" button. We collect data on how recommendations change throughout these phases in order to characterize how well YouTube's recommendation system responds to these sock puppets' various interactions with the system.

We then run a user survey on Qualtrics to understand how users interact with the features that we tested. (TODO). 

#### Findings
* Main finding- the most effective way to remove unwanted content recommendations, out of those we tested, was the "Not interested" button: using this button removed 97% of videos from an unwanted topic on the homepage. 
* However, from a user survey, we estimate that 44% of the YouTube adult population is unaware that this button exists.
* Other finding- unwanted videos are much harder to remove on the videopage than they are on the homepage.
* Other finding- we find evdience of YouTube implementing measures to refuse recommending new content creators to users on topics that are offensive and triggering, aprticularly from the Alt-Right. 
* Other finding- we find evidence consistent with theoretical critiques of the filter bubble hyptotehesies- in contrast to popular media fears and what the term "filter bubble" would suggest, videos from an unwanted topic never reached more than half of one's recommendaitons.

Methods

This project uses the Selenium web testing software to simulate users. It uses the [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver) package to avoid bot detection. Data is written into Amazon S3.

## Included files

* scrubber.py - class for the sock puppet. It includes code to log into, interact with, collect data from, and watch videos on YouTube
* scrub_main.py - run the experiment by specifying the actions to be performed by the bot during each phase
* seed_data_generation/ - generate the videos that our bots watch during the "stain phase" by querying the YouTube API for videos from selected topics
* analysis/ - analysis script of data after performing manual labeling, answering the RQ's of our paper



## Musings

### Data Collection

Seed data generation
- files: ./seed_data_generation/
- bots are assigned one of four topics: ABCD
- for each, we start with a csv containing channels of interest. Then, we query the YouTube API for (SETTINGS) videos from each sample. These videos serve as the pool of starting videos for our sock puppets.

Sock puppet data collection pipeline
- files: ./scrub_main.py and ./scrubber.py
- Phases are "stain phase", then "scrub phase"
- (TODO) Diagrams: Algorithm and flowchart

Sock puppet technicalities
- files: (Rob's code), communities/, runs/, runner.py
- sock puppets each have their own Google account, and uses Selenium with the undetected-chromedriver package to interact with YouTube and scarpe data, while evading Google restrictions
- uses terraform to create an AWS EC2 swarm, and saves data to AWS S3

### Data Analysis- bots

First pass analysis- 
- incorrect labeling: using the channel lists that exist
- (TODO) cool plot: It looks like some features are better than others!
- (TODO) making a mixed effects logistic regression model, and ranking the coefficients to find the most influential variable (i.e. most effective scrubbing strategies). We see that the "not-interested" strategy works best!
- (TODO) another cool plot: stackplots on the types of categories within the AIN shows that for some strategies, all 
- Next, I estimated the conditional probability that the bot did interact with the system, given that it should have interacted, so that I could understand the efficacy of the startegy


Data labeling- doing it less naively
