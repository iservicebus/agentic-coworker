
# List of API Document URLs

## Arxiv papers
**search link**: https://info.arxiv.org/help/api/user-manual.html

## SEC company filings

**search link**: https://sec-api.io/docs/full-text-search-api

**more links**: https://sec-api.io/docs



## FRED economics data

**search link**: https://fred.stlouisfed.org/docs/api/fred/series_search.html

**more links**: https://fred.stlouisfed.org/docs/api/fred/


## Alpha Avantage API - Capital Market
**API docs**: https://www.alphavantage.co/documentation/


## Google Productuvity APIs

### profile
**profile**: https://developers.google.com/workspace/gmail/api/reference/rest/v1/users/getProfile

### gmail 
**sending email**: https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send

https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list
https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get

https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/delete

### calendar
calendar list: https://developers.google.com/workspace/calendar/api/v3/reference/calendarList/list

https://developers.google.com/workspace/calendar/api/v3/reference/calendarList/get

https://developers.google.com/workspace/calendar/api/v3/reference/calendars/insert

calendar events:
https://developers.google.com/workspace/calendar/api/v3/reference/events/list
https://developers.google.com/workspace/calendar/api/v3/reference/events/insert

https://developers.google.com/workspace/calendar/api/v3/reference/events/list

### drive
https://developers.google.com/workspace/drive/api/reference/rest/v3/about/get

https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list

https://developers.google.com/workspace/drive/api/reference/rest/v3/files/get
https://developers.google.com/workspace/drive/api/reference/rest/v3/files/create

https://developers.google.com/workspace/drive/api/reference/rest/v3/files/download

### doc

https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/get

https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/create

### youtube
https://developers.google.com/youtube/v3/docs/search/list?apix_params=%7B%22part%22%3A%5B%22snippet%22%5D%7D

https://developers.google.com/youtube/v3/docs/videos/list

https://developers.google.com/youtube/v3/docs/videos/insert

### sheets
https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/get
https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/create



## Github APIs

https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28

https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28

https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28

https://docs.github.com/en/rest/orgs/orgs?apiVersion=2022-11-28


## linked APIs

**share link**: https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin
**profile link**: https://learn.microsoft.com/en-us/linkedin/shared/integrations/people/profile-api?context=linkedin%2Fconsumer%2Fcontext




# Calendly

https://developer.calendly.com/api-docs/d7755e2f9e5fe-calendly-api



# google
https://console.cloud.google.com/
	1.	Go to Google Cloud Console → APIs & Services → OAuth consent screen
    choose client and create client


API scope:

Use Case
Recommended OAuth Scope
Send email via Gmail API.  https://www.googleapis.com/auth/gmail.send
Access user profile & email. https://www.googleapis.com/auth/userinfo.profile/.../userinfo.email

Access specific profile details.  https://www.googleapis.com/auth/user.emails.read (or similar)
View & create Google Calendar events.  https://www.googleapis.com/auth/calendar.events


# github


https://github.com/settings/apps


https://github.com/github/rest-api-description/tree/main/descriptions/ghes-3.14

https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-repositories-for-a-user



for github, following scopes are required:

read:user, user, user:email, user:follow  -   Access to profile, email, follow/unfollow permissions

read:org, write:org, admin:org     -  Org membership and project access at varying levels

repo    - Full access to all repos (public & private) + org-related controls

read:user user:email user:follow read:org repo   write:org admin:org



# linkedin 

https://developer.linkedin.com/

https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2?context=linkedin%2Fconsumer%2Fcontext

https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin

# SAP Sandbox

https://api.sap.com/api/salesorder/tryout

https://api.sap.com/api/contact/overview

https://api.sap.com/api/installedbase/overview

https://api.sap.com/api/salespricelist/overview

https://api.sap.com/api/stocklocation/overview

https://api.sap.com/api/OrderDeliverySchedulesService/overview

https://api.sap.com/api/EventService/overview


# ServiceNow

https://developer.servicenow.com/dev.do#!/reference/api/washingtondc/rest/c_TableAPI


# salesforce

https://developer.salesforce.com/docs/marketing/marketing-cloud-growth/references/mc-rest-leads?meta=getLead


# finnhub

https://finnhub.io/static/swagger.json


# deep Research

## web search
    Tavily Extract: Tavily's dedicated content extraction endpoint that can extract and clean content from specific URLs without performing searches
    Jina Reader: A powerful web content extraction service that converts web pages to clean, LLM-friendly text by simply prepending https://r.jina.ai/ to any URL
    Firecrawl: A comprehensive web scraping platform that converts websites into clean markdown or structured data, with advanced features like JavaScript rendering and sitemap crawling
