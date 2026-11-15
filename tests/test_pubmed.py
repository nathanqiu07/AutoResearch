"""WS B public-track harvest: PubMed lists her papers with full-text URLs, real dates and her position."""
import unittest

from autoresearch.taste.pubmed import parse_pubmed

XML = b"""<PubmedArticleSet>
<PubmedArticle><MedlineCitation><Article>
  <ArticleTitle>A programmable dual-RNA-guided DNA endonuclease.</ArticleTitle>
  <AuthorList><Author><LastName>Jinek</LastName><ForeName>Martin</ForeName></Author>
    <Author><LastName>Doudna</LastName><ForeName>Jennifer A</ForeName></Author>
    <Author><LastName>Charpentier</LastName><ForeName>Emmanuelle</ForeName></Author></AuthorList>
  <ArticleDate DateType="Electronic"><Year>2012</Year><Month>06</Month><Day>28</Day></ArticleDate>
</Article></MedlineCitation>
<PubmedData><History><PubMedPubDate PubStatus="pubmed"><Year>2012</Year><Month>6</Month><Day>30</Day></PubMedPubDate></History>
<ArticleIdList><ArticleId IdType="pubmed">22745249</ArticleId><ArticleId IdType="pmc">PMC6286148</ArticleId>
<ArticleId IdType="doi">10.1126/science.1225829</ArticleId></ArticleIdList></PubmedData></PubmedArticle>
<PubmedArticle><MedlineCitation><Article>
  <ArticleTitle>CRISPR in the clinic.</ArticleTitle>
  <AuthorList><Author><LastName>Doudna</LastName><ForeName>Jennifer A</ForeName></Author></AuthorList>
</Article></MedlineCitation>
<PubmedData><History><PubMedPubDate PubStatus="pubmed"><Year>2020</Year><Month>3</Month><Day>4</Day></PubMedPubDate></History>
<ArticleIdList><ArticleId IdType="pubmed">111</ArticleId><ArticleId IdType="doi">10.1/xyz</ArticleId></ArticleIdList></PubmedData></PubmedArticle>
<PubmedArticle><MedlineCitation><Article>
  <ArticleTitle>Soil microbes of the Midwest.</ArticleTitle>
  <AuthorList><Author><LastName>Smith</LastName><ForeName>Ann</ForeName></Author>
    <Author><LastName>Doudna</LastName><ForeName>Kevin</ForeName></Author></AuthorList>
</Article></MedlineCitation>
<PubmedData><History><PubMedPubDate PubStatus="pubmed"><Year>2019</Year><Month>1</Month><Day>2</Day></PubMedPubDate></History>
<ArticleIdList><ArticleId IdType="pubmed">222</ArticleId></ArticleIdList></PubmedData></PubmedArticle>
</PubmedArticleSet>"""


class PubmedListingTest(unittest.TestCase):
    def setUp(self):
        self.listed = parse_pubmed(XML, "Jennifer Doudna")

    def test_paper_with_pmc_copy_is_listed_by_its_full_text_url_and_electronic_date(self):
        self.assertEqual(self.listed["https://pmc.ncbi.nlm.nih.gov/articles/PMC6286148/"], {
            "authors": ["Martin Jinek", "Jennifer A Doudna", "Emmanuelle Charpentier"],
            "published": "2012-06-28", "title": "A programmable dual-RNA-guided DNA endonuclease."})

    def test_paper_without_pmc_copy_falls_back_to_doi_and_pubmed_date(self):
        self.assertEqual(self.listed["https://doi.org/10.1/xyz"]["published"], "2020-03-04")

    def test_paper_by_someone_else_with_her_surname_is_left_out(self):
        self.assertEqual(len(self.listed), 2)


if __name__ == "__main__":
    unittest.main()
