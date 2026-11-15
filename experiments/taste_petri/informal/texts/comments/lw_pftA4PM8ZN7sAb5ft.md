Comment by Owain_Evans, 2020-09-23, on "Forecasting Thread: Existential Risk"
https://www.lesswrong.com/posts/6x9rJbx9bmGsxXWEj/forecasting-thread-existential-risk-1?commentId=pftA4PM8ZN7sAb5ft

HIS COMMENT:
I've made a distribution based on the [Metaculus](https://www.metaculus.com/questions/2568/ragnar%25C3%25B6k-question-series-results-so-far/) community distributions:

![](https://39669.cdn.cke-cs.com/rQvD3VnunXZu34m86e5f/images/eb89b3044524aaf915b4a85e72a7dc87c44f5b456bb9387c.png)

![](https://39669.cdn.cke-cs.com/rQvD3VnunXZu34m86e5f/images/d2ca4751d24965c9a365ab51ec1907d726d090c2114ab39c.png)

(I used [this](https://colab.research.google.com/drive/15ZXqMmuPIsmqC7j-wiR3pvPFm83qpk2K?usp=sharing#scrollTo=vtg58ReV5lcL) Colab notebook for generating the plots from Elicit distributions over specific risks. My Elicit snapshot is [here](https://elicit.ought.org/builder/YP-aCltlB)).   
  
In 2019, Metaculus posted the [results](https://www.metaculus.com/questions/2568/ragnar%25C3%25B6k-question-series-results-so-far/) of a forecasting series on catastrophic risk (>95% of humans die) by 2100. The overall risk was 9.2% for the community forecast (with 7.3% for AI risk). To convert this to a forecast for existential risk (100% dead), I assumed 6% risk from AI, 1% from nuclear war, and 0.4% from biological risk. To get timelines, I used Metaculus forecasts for [when](https://www.metaculus.com/questions/2805/if-there-is-an-artificial-intelligence-catastrophe-this-century-when-will-it-happen/) the AI catastrophe occurs and for [when](https://www.metaculus.com/questions/4441/when-will-be-the-next-great-power-war/) great power war happens (as a rough proxy for nuclear war). I put my [own](https://elicit.ought.org/builder/FwX1ulAuS) uninformative distribution on biological risk.  
  
This shouldn't be taken as the "Metaculus" forecast, as I've made various extrapolations. Moreover, Metaculus has a separate [question](https://www.metaculus.com/questions/578/human-extinction-by-2100/) about x-risk, where the current forecast is 2% by 2100. This seems to me hard to reconcile with the 7% chance of AI killing >95% of people by 2100, and so I've used the latter as my source.   
  
Technical note: I normalized the timeline pdfs based on the Metaculus binary probabilities in this [table](https://www.metaculus.com/questions/2568/ragnar%25C3%25B6k-question-series-results-so-far/), and then treated them as independent sources of x-risk using the [Colab](https://colab.research.google.com/drive/15ZXqMmuPIsmqC7j-wiR3pvPFm83qpk2K?usp=sharing#scrollTo=vtg58ReV5lcL). This inflates the overall x-risk slightly. However, this could be fixed by re-scaling the cdfs.