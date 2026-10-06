## F-0043-01
stelle: Hinweisbox „Important" zu Beginn des Dokuments
version: V-2026-10-06
zitat: >
  Your prompts (inputs) and completions (outputs), your embeddings, and your training data: are NOT available to other customers. are NOT available to OpenAI or other providers of Models sold by Azure. are NOT used by providers of Models sold by Azure to improve their models or […]

## F-0043-02
stelle: Abschnitt „Generating completions, images or embeddings through inferencing"
version: V-2026-09-12
zitat: >
  Prompts and responses are processed within the customer-specified geography (unless you are using a Global or DataZone deployment type), but may be processed between regions within the geography for operational purposes (including performance and capacity management). See below […]

## F-0043-03
stelle: Abschnitt „Understanding location of processing for 'Global' and 'Data zone' deployment types"
version: V-2026-09-12
zitat: >
  In addition to standard deployments, Foundry offers Models sold by Azure deployment options labeled as 'Global' and 'DataZone.' For any deployment type labeled 'Global,' prompts and responses may be processed in any geography where the relevant model sold by Azure is deployed […]

## F-0043-04
stelle: Abschnitt „Data storage for Models sold by Azure features", Absatz zu Abuse Monitoring
version: V-2026-09-12
zitat: >
  For automated review, customer's prompts and completions are not stored by the system or used to train the AI models or other systems. The abuse monitoring data store where prompts and completions are stored for human review is logically separated by customer resource (each […]

## F-0043-05
stelle: Abschnitt „Data storage for Models sold by Azure features", Aufzählungspunkt zur Verschlüsselung
version: V-2026-09-12
zitat: >
  Is always encrypted at rest with Microsoft's AES-256-encryption by default, with the option of using a customer managed key (certain preview features may not support customer-managed keys). Microsoft-managed keys are always used to ensure baseline encryption for all stored data.