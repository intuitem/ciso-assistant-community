# Metrics

### Expected outcome

* define your metrics or import their definition
* instantiate them on your domains
* feed data to your metric instances
* create dashboards with builtin and custom metrics

### Key concepts

```mermaid
graph TD
  metric_definition --> metric_instance --> metric_sample
  dashboard --> dashboard_widget_custom --> metric_instance
  dashboard --> dashboard_widget_builtin
  dashboard --> dashboard_text
```



***

## Metric definitions

Consider metric definition as a template of your metric. It serves as the guideline of the actual metric instance that you will track accross your domains.

### Importing definitions

#### 1. Introduction

You will learn how to import off-the-shelf metrics definitions on CISO Assistant.

![Introduction](https://static.guidde.com/v0/qg%2FJ0RVKao966SmT5uQXRHVpcgc2yd2%2FvTb9cHNSPqash2GGUZdeys%2F8Q3gdFyrUPF4skriW4JL7M_doc.png?alt=media\&token=11940028-5485-4889-87b7-01257a9ae71b)

#### 2. Open Metric Definitions

Click "Metric definitions".

![Open Metric Definitions](https://static.guidde.com/v0/qg%2FJ0RVKao966SmT5uQXRHVpcgc2yd2%2FvTb9cHNSPqash2GGUZdeys%2FhoqCSfxdDNPGFAJfuQKuYJ_doc.png?alt=media\&token=32b9f469-998f-436e-a68f-2f2f63a2c7ef)

#### 3. Click import

Click here to proceed to the next menu.

![Click import](https://static.guidde.com/v0/qg%2FJ0RVKao966SmT5uQXRHVpcgc2yd2%2FvTb9cHNSPqash2GGUZdeys%2FvcwEUhbs8ZrAacw8QJgFMU_doc.png?alt=media\&token=796e72b7-a370-480e-9155-cf9c73a50e8e)

#### 4. Import the library matching your criteria

You can also preview the content before importing it.

![Import the library matching your criteria](https://static.guidde.com/v0/qg%2FJ0RVKao966SmT5uQXRHVpcgc2yd2%2FvTb9cHNSPqash2GGUZdeys%2F9TmRRuzyLXwZxEYvXfTakF_doc.png?alt=media\&token=25d4a3b1-11fb-45f8-a836-75eec79c783a)

#### 5. Return to Metric Definitions

Click "Metric definitions" to revisit the main metrics page.

![Return to Metric Definitions](https://static.guidde.com/v0/qg%2FJ0RVKao966SmT5uQXRHVpcgc2yd2%2FvTb9cHNSPqash2GGUZdeys%2F4wTQWHiwwYZoU6xvvinm9t_doc.png?alt=media\&token=bc756aa3-f19a-4bb3-a890-6cd0513f877f)

#### 6. Look for the metric definition you want

Click "Search..." to begin finding specific metrics.

![Look for the metric definition you want](https://static.guidde.com/v0/qg%2FJ0RVKao966SmT5uQXRHVpcgc2yd2%2FvTb9cHNSPqash2GGUZdeys%2F4PceckBSLsN6G5GJsgz1gH_doc.png?alt=media\&token=90b71177-1ed2-4f65-9775-622fa064fcd7)

#### 7. Select The Specific Metric

You can now instantiate this metric as you see fit for your domains.

![Select The Specific Metric](https://static.guidde.com/v0/qg%2FJ0RVKao966SmT5uQXRHVpcgc2yd2%2FvTb9cHNSPqash2GGUZdeys%2F11dAiGvXZQ1oazVXaVYEKj_doc.png?alt=media\&token=f8d96903-dfeb-41e4-a7e8-3dcae9d05990)

You can now instantiate this metric as needed across your domains. Keep in mind that you can also create your own metric definition directly without going through the library.



### Creating a definition

Metrics can be quantitative (number with unit) or qualitative (choices):

<figure><img src="../.gitbook/assets/image (51).png" alt=""><figcaption><p>Quantitative metric</p></figcaption></figure>

You can add your options during declaration or afterward:

<figure><img src="../.gitbook/assets/image (52).png" alt=""><figcaption><p>Qualitative metric</p></figcaption></figure>

The "higher is better" setting is used to indicate if the trend is a good thing or not.

***

## Metric instance

The metric instance is the projection of the definition to a specific domain and it's _what you'll be tracking_.&#x20;

<figure><img src="../.gitbook/assets/image (53).png" alt=""><figcaption></figcaption></figure>



Parameters:

* Metric definition (it will inherit its settings)
* Domain: the scope of this metric
* Status: lifecycle of the metric. The stale is specially interesting as the application will auto-toggle it according to the data freshness
* Collection frequency: expected collection frequency, on which we add a grace period before toggling the metric to stale status
* Target value: expected target of this metric for this specific domain. This is handy as you can have different targets of the same metric definition according to the domain.
* Assigned to: owner of the metric instance and its update.



## Metric sample

This is the actual data of the metric instance on a given timestamp.&#x20;

<figure><img src="../.gitbook/assets/image (54).png" alt=""><figcaption></figcaption></figure>

Keep in mind that you can add the data manually or through all the supported integrations (API, n8n, etc.). Note that data cannot be in the future.



<figure><img src="../.gitbook/assets/image (55).png" alt=""><figcaption></figcaption></figure>

## Dashboards



Dashboards are the visual representation of the metrics and support:

* custom metrics instance (multiple charts)
* built-in metrics (multiple charts)
* markdown text widget

<figure><img src="../.gitbook/assets/image (56).png" alt=""><figcaption></figcaption></figure>

In edit mode, you can add different widgets, place and resize them as you see fit:

<br>

<figure><img src="../.gitbook/assets/image (57).png" alt=""><figcaption></figcaption></figure>

Once done, you can go back to view mode to see the result:

<figure><img src="../.gitbook/assets/image (58).png" alt=""><figcaption></figcaption></figure>



In addition to the custom metrics for your internal KPI and KRI, you can also include some of the built-in metrics tracked by the platform:\
\
![](<../.gitbook/assets/image (59).png>)

Those are updated on each change of your data and tracked as daily metrics.
