# youtube-burst


This project uses code scripts to simulate YouTube users. These scripts detail the behavior of a given simulated user. Many of these "sock puppets" are run in parallel in the cloud, which is detailed a separate [project](https://github.com/carleski/ytburst-terraform), with the help of Rob Carleski. Together, these sock puppet scripts serve as the data collection portion of a paper on YouTube user agency and ability to contest bad recommendations. It is currently under review at ICWSM. 

## Description

Can YouTube users effectively remove unwanted recommendations? We use sock puppets built with Selenium to answer this question. Broadly, these sock puppets first purposely populate their feed with videos from this unwanted topic ("stain phase"); Then, they take on one of a variety of strategies to try to eliminate such videos from being recommended ("scrub phase"). These strategies correspond to different features on YouTube that one could use to indicate disinterest towards certain videos, such as the "Not Interested" button, the "Dislike" button, and the "Delete from watch history" button. We collect data on how recommendations change throughout these phases in order to characterize how well YouTube's recommendation system responds to these sock puppets' various interactions with the system. 

## Included files

* scrubber.py - class for the sock puppet. It includes code to log into, interact with, collect data from, and watch videos on YouTube
* driver.py - [TODO]
