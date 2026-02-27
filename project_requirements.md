# LichtBlick AI Engineer Coding Challenge

## "Agentic Customer Contact Copilot"

At LichtBlick, we receive a lot of email requests from our customers. These emails frequently include similar intents like personal/payment information changes, meter readings, contract issues or product questions. For these repetitive processes we want to introduce a (semi-)automated solution that helps us to reduce **Average Handle Time (AHT)** and increase **First-Contact Resolution (FCR)** without compromising quality, compliance or customer trust.

---

## Requirements

### 1. Workflow Steps

Create a workflow that covers all or most of these steps:

- **a)** Text extraction from an email file
- **b)** Intent detection
- **c)** Data extraction
- **d)** Handling each intent (or at least one)
- **e)** Result aggregation (compose answer to client)

---

### 2. Authentication & Intent Handling

#### Authentication Rules

Depending on the intent, you need to authenticate the customer before executing any sub-process:

| Intent | Description | Auth Required |
|---|---|---|
| `MeterReadingSubmission` | Customer submits or corrects electricity meter reading | Yes |
| `PersonalDataChange` | Name, address or payment info updates | Yes |
| `ContractIssues` | Question about termination, contract duration or switching | Yes |
| `ProductInfoRequest` | Question about tariffs, dynamic pricing, green energy... | No |
| `GeneralFeedback` | Compliments, complaints or open comments | No |

#### Authentication Method

Authentication can be done with **three personal data points** extracted from the email:
- Contract number
- Full name
- Postal code

> **Optional:** If the customer did not provide authentication data in the initial email, ask for it via email response.

> **Optional:** If you have multiple intents (with or without authentication), think about the best way to handle them so that authentication is done only once, but processing can be parallelized.

---

### 3. Example Email Exchange

**CUSTOMER → LICHTBLICK**

> Hello LichtBlick Team,
>
> I'd like to submit my latest electricity meter reading and ask about your dynamic tariff. My meter number is LB-9876543. The reading yesterday (25.09.2025) was 2438 kWh.
>
> How does your dynamic tariff work and would it make sense for a 2-person household with an induction stove and no EV? Do prices change hourly and can I switch any time?
>
> I can't find my contract number right now - if you need it, tell me what to provide.
>
> Thanks a lot, Julia Meyer

---

**LICHTBLICK → CUSTOMER**

> Hello Ms. Meyer,
>
> I'm your AI-powered service assistant. To process your request, we need your customer number in addition to your meter number (LB-9876543) and one of the following verification details:
> - Contract number
> - Full name of the contract holder
> - Postal code of customer address
>
> Simply reply to this email, and we will get back to you promptly to assist you.
>
> Additionally, here are some information on our Dynamic Tariff:
>
> Our dynamic electricity tariff reflects wholesale market prices, which may vary throughout the day.
> - **Who benefits:** Customers who can shift certain energy usage to lower-price periods (e.g., operating household appliances during off-peak hours).
> - **Requirements:** A compatible smart meter is generally necessary.
> - **Switching process:** You may request a tariff change via the checkout or the customer portal.
>
> Kind Regards

---

**CUSTOMER → LICHTBLICK**

> Hello,
>
> Sure, my postal code is 20097.
>
> Best, J. Meyer

---

**LICHTBLICK → CUSTOMER**

> Dear Ms. Meyer,
>
> This is your AI-powered service assistant. While reviewing your meter reading, I noticed that your consumption of 2438 kWh for the recent period appears unusually high.
>
> I kindly ask you to double-check the data or let us know the reason for this possible deviation. Common reasons may include:
> - Construction work (e.g., contractors, drying processes)
> - New family members or additional occupants
> - New tech equipment, sauna, electric vehicle, etc.
>
> Simply reply to this email, and we will get back to you promptly to assist you.
>
> Kind Regards

---

**CUSTOMER → LICHTBLICK**

> Sorry, I mistyped the consumption. The correct value is 1438 kWh.
>
> Best, Julia M

---

**LICHTBLICK → CUSTOMER**

> Dear Ms. Meyer,
>
> This is your AI-powered service assistant. Thank you for submitting your meter reading!
>
> We have successfully recorded your meter reading in our system. Your request is now completed. Should you have any further concerns, please feel free to contact us at any time.
>
> Kind Regards

---

### 4. Orchestration

Start with a single intent and add authentication. The ideal solution would include handling a customer mail with **at least two intents** (one with and one without authentication). Think about how to orchestrate multiple tasks:

- **Sequentially** — e.g., with shared state for the authentication result
- **In parallel** — for independent subtasks that can run safely concurrently

### 5. Tech Stack

Preferred stack is **Azure**, **Semantic Kernel**, and **C#/.NET**, but you may also use **LangChain & LangGraph** or another popular framework of your choice (or none).

### 6. Mocking

All API calls, sending/receiving emails, and authentication can be mocked with:
- Text files
- Console I/O
- Your favorite mocking library

### 7. NFRs *(Optional)*

Your solution should also address non-functional requirements such as:
- Observability
- Reliability
- Data protection & security

### 8. Tests *(Optional)*

Add tests to execute your solution with different email inputs.
