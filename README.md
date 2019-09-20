# DABCAT2.0

DABCAT2.0 is marked improvement over DABCAT1.0. It's purpose is entirely the same, but it's operation is completely different. Rather than hardcoding action results in the "dummy" app code itself, DABCAT2.0 "dummy" apps pull from a dynamic list of cached action results that are maintained in the Phantom instance on which the "dummy" app is installed. This change in design allows for new action results to be added to the cache without recompiling the "dummy" app. Additionally, because cached data is maintained in Phantom, significantly more people can add content to the action results cache on a given instance.

# Prerequisites to running DABCAT2.0

**Python dependencies**
* click
* pyfiglet
* colorama
* termcolor
* PyInquirer

These can bee installed with pip

# Where to run DABCAT2.0

Just like DABCAT1.0, DABCAT2.0 should be run from the source code directory of the app that will be "dummied" up.

Example Directory Structure:
* Documents
  * Dev
    * Projects
      * DABCAT2.0
        * dabcat2.py
    * bitbucket
      * office365
        * <app code goes here>
        
 in this example I'd run DABCAT2.0 from /Documents/Dev/bitbucket/office365 like so:
 
 ```python ../../Projects/DABCAT2.0/dabcat2.py```

# Creating a "dummy" app with DABCAT2.0

When first launching DABCAT you should see the following:

```
Here's what we already know:
      connector file: ./connector_file_name.py
      metadata file: ./metadata_file.json
```

If you don't see this, you're probably running Phantom from the wrong directory. See **Where to run DABCAT2.0**

DABCAT2.0 asks only 5 questions of you when creating a new Dummy APP.
1. Is this correct?
  - Is this information that "we already know" correct. If not you're probably running DABCAT2.0 from the wrong directory.
2. What do you want to call this app...?
  - This is the name of the new "dummy" app. You should not name it the same thing as the production app or **you're gonna have a bad time**. DABCAT will make a suggestion for an App name, you should probably use this.
3. What do you want to call this product...?
  - Same advice as number 2
4. What do you want to use for the appid...?
  - If you're rebuilding a dummy app that already exists, get the appid from it, and use that. Do no use the same appid for different apps. If you do this **you're gonna have a bad time**. 
5. Do you want the app to fail if no matching action/parameter combinations and no default action results are found?
  - If someone submits something for which you don't already have cached results, and no default is selected, do you want an error to occur? If you unsure on this - say "yes"
 
 You'll have a an option to review some data.
 Ex:
```
 Here's a review
        dummy app name: VirusTotal DEV
        dummy app product name: VirusTotal DEV
        dummy app appid: 50ea6888-07d8-44bf-aa4a-77f84f605dc8
```

* yes, i know it's not everything.. but do you feel confident that this is all correct?
  - You are almost always going to say yes here unless you fat fingered something
  
Finally output will be presented acknowledging that the app was created, compiled and tar'd. Ex:
```
congratulations! you're done - go try out your shiny new app
        /Users/iforrest/Documents/Dev/bitbucket/virustotal_dev_dummy.tgz
        /Users/iforrest/Documents/Dev/bitbucket/virustotal_dev_dummy <- source files here
```

# Configuring Phantom to use a DABCAT2.0 created app

The first thing you must do is add a PHANTOM_API_KEY environment variable. The API key should belong to an automation user with "127.0.0.1" as the allowed IP. The PHANTOM_API_KEY environment variable should be marked "secret" with the "secret" checkbox. You can add an environment variable by going here:
```
Administration->Administration Settings->App Environment
```

Next you must add a label called "demo_configuration". This can be done by going here:
```
Administration->Event Settings->Label Settings
```

**You should make sure that this label is only accessible to admin users. Demo users/workshop users/BOTS users should not have access to this label**

Lastly, you must install your app. You can do this by going to **Apps** and the clicking **Install App**. Select the zipped tarball that was created for you by DABCAT2.0

# Adding action result data to be used by a DABCAT created app

All action result data will be maintained and managed by adding containers, artifacts, and files to the "demo_configuration" label you created in the **Configuring Phantom to use a DABCAT2.0 created app** section.

**If you want to supply a cached action result json when a specific parameter is provided to a DABCAT app, action do the following:**

1. Create a container in the "demo_configuration" label
  * The container name must match EXACTLY the product name of the DABCAT created app that you wish to supply cached data to. 
    * If you are unsure of the product name, you can look in the *.json file for the **product_name** key.
  * The description should be the action identifier for the action of the DABCAT created app to which you want to supply cached data. 
    * If you are unsure of the action identifier, you can look in the *.json file for the **name** of the action under the **actions** key. Once you have found the right action look at the **identifier** key. Generally these will be the very closely aligned but sometimes they are not (e.g. virustotal action name is "url reputation" but the identifier is "lookup_url")
2. Upload the action results json you'd like to use to the "files" (previously known as "vault") area of your new container.
  * copy the vaultId from this area after successful upload
3. Create an artifact titled **matching criteria**
4. Add the following CEF fields to the artifact:
  * vaultId - This should be the vaultId that points to your uploaded action results json
  * <parameter_name> - This is the parameter you want to match to determine if this action result data should be returned
    * You can have as many <parameter_name> fields as you'd like. They will be "and"'d together.

**Example:** If I want to return cached action results for a VirusTotal URL reputation check when someone passes in "http://www.google.com" as the **url** parameter, I'd do the following. In this example the Vendor Name of my DABCAT created app is "virustotal DEV":
1. Create a container called "virustotal DEV" with a description of "lookup_url"
  * note: the the identifier of the url reputation action for virustotal is "lookup_url"
2. Upload action results from a previously executed lookup of "http://www.google.com" to the files area of the container.
3. Create an artifact called "matching criteria" with the following fields:
  * vaultId - The vaultId from the file Iuploaded in step 2
  * url - http://www.google.com
    * this will ensure that when someone passes a url of http://www.google.com to the URL reputation of my DABCAT created virustotal app that I get my cached results.
    
# Providing Default Data to an action

There may be some cases where you want to provide default data to an action regardless of the input. Follow the steps outlined in the section called **Adding action result data to be used by a DABCAT created app**. However, when you create your artifact instead of providing <parameter_names> for matching, simply add a "dummy_default" cef field and set the value to "True."

# Replacing Results Data at RunTime:

Replacements are handled via json file called replacerizer.json. You'll want to upload this to your container and add a "replacerizer" field to your "matching criteria" artifact with the value set to the vaultId of your uploaded replacerizer.json file.

For simple replacements the key of the JSON value in replacerizer.json is used as the value to search for, and the value is the replacement value. If I wanted to replace all instances of the word "Positives" with "Bad-Guy-Count", I'd do the following:

```
{
  "Positives": "Bad-Guy-Count"
}
```

For dynamic replacements a special syntax is used. A dynamic replacement is a replacement of some data in the results json with a parameter that was provided at run time to the app. This is particularly useful in conjunction with **default data**. To do the replacement, values should be crafted as such - \*\*\*<parameter_name>\*\*\*.

For example if I want to replace all instances of "http://www.google.com" with the url parameter that is passed into the action at run time I'd do the following:

```
{
  "http://www.google.com": "***url***"
}
```

# Dummying actions that return files and/or add artifacts

Some actions create new artifacts in the container against which they were run (like "extract ioc"). Others create file records, like "get file". Getting a DABCAT created action to do this is very easy. In addition to the action results json being uploaded and the "matching criteria" artifact being created, any other artifacts and/or files that exist in the container will get added to the container against which the dummy action is run. No special configuration or changes need to be made.

# Supplying cached Poll Data

1. In this case just as in **Adding action result data to be used by a DABCAT created app** we will need to create a container with the product name as the name.
2. The description of the container should be "on_poll"
3. You will upload exported phantom containers that you want to use as poll results to this container.
  * For instance, if I have a phantom system that has emails that I want to return as part of the Poll action of dummy office 365 app, I would export those containers from that phantom system, and import them to the "files" are of this container.
4. For each container you want to provide when polling actions occur, create an artifact.
  * The name of the artifact should be "poll artifact"
  * The artifact should consist of two fields:
    * vaultId - corresponding to the vaultId of the record you want returned upon polling
    * label - the label that you would like the poll results added to
