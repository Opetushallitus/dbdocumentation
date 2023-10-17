# dbdocumentation
Tietokantadokumentaatiota generoiva sovellus

## Komponentit
- Python-ohjelma, joka käynnistää ja instrumentoi java-ohjelmia
- [Schemaspy](https://schemaspy.org)
- [Postgres jdbc-ajuri](https://jdbc.postgresql.org)

## Ratkaisu
Sovellusta ajetaan ajastetusti kerran kuukaudessa. Sovellus tuottaa tiedostoja S3-ämpäriin, josta dokumentaatiota tarjoillaan cloudfrontin avulla.