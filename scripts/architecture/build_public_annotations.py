"""Closed public reading projection and shared candidate-level counting contract."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def build():
    profile=json.loads((ROOT/'ontology/cile-review-profile.yaml').read_text())
    archive=json.loads((ROOT/'ontology/modules/annotation-archive.json').read_text())
    obj=lambda props:dict(type='object',additionalProperties=False,required=list(props),properties=props)
    string=lambda n:dict(type='string',maxLength=n)
    array=lambda item,n:dict(type='array',maxItems=n,items=item)
    count=dict(type='integer',minimum=0)
    digest=dict(type='string',pattern='^[a-f0-9]{64}$')
    category={'enum':['aetiology','diagnosis','screening','therapy','prognosis','prevention']}
    field=obj({'field_name':{'enum':sorted({v for values in archive['field_names'].values() for v in values})},'value':string(12000)})
    section=obj({'scope':{'enum':list(archive['field_names'])},'group_label':string(100),'fields':array(field,2000)})
    claim=obj({'category':category,'role':{'enum':['primary','secondary','alternative']}})
    annotation=obj({'annotation_id':digest,'assessment_state':{'const':'unreviewed_manual_support'},'source_url':string(2000),'updated_at':string(64),'sections':array(section,100),'classes':array(claim,1000),'unparsed_lines':count})
    schema={'$schema':'https://json-schema.org/draft/2020-12/schema',**obj({'schema_version':{'const':1},'projection_version':{'const':'CILE-PUBLIC-ANNOTATIONS-1'},'candidate_id':{'type':'string','pattern':'^CAND-[A-Za-z0-9-]{1,100}$'},'annotations':array(annotation,100),'conflicts':count,'revision':digest})}
    (ROOT/'schema/public-annotations.schema.json').write_text(json.dumps(schema,indent=2)+'\n')
    def mapping(spec,path=''):
        out={}
        for name,child in spec.get('properties',{}).items():
            pointer=path+'/properties/'+name
            known={'schema_version':'extraction_schema_version','projection_version':'schema:version','annotations':'schema:hasPart','sections':'schema:hasPart','fields':'schema:hasPart','classes':'extraction_framework','conflicts':'public_annotation_conflicts','revision':'schema:version','candidate_id':'candidate_id','annotation_id':'annotation_id','source_url':'source_url','updated_at':'ingress_updated_at','assessment_state':'annotation_review_state','scope':'annotation_scope','group_label':'v2_heading','field_name':'annotation_field','value':'extraction_value','role':'annotation_class_role','category':'extraction_category','unparsed_lines':'annotation_unparsed_lines'}
            out[pointer]=known.get(name,'schema:'+name);out.update(mapping(child,pointer))
        if 'items' in spec:out.update(mapping(spec['items'],path+'/items'))
        return out
    module={'profile_version':profile['version'],'projection_version':'CILE-PUBLIC-ANNOTATIONS-1','schema':'schema/public-annotations.schema.json','schema_class':'AssistantRecommendation','schema_field_slots':mapping(schema),
            'privacy_boundary':'Only curator-authorised unreviewed reading fields reconstructed from the archive; no browser parsing of GitHub, private source snapshots, attribution, reviewer identities or working notes.',
            'review_boundary':'Annotation groups are not ReportedStudy/ReportedAnalysis records. Multiple current annotations coexist; original alternatives and conflicts never become scientific decisions.'}
    (ROOT/'ontology/modules/public-annotations.json').write_text(json.dumps(module,indent=2)+'\n')
    path=ROOT/'schema/public-enrichment-index.schema.json';index=json.loads(path.read_text());index['properties']['projection_version']['const']='CILE-PUBLIC-INDEX-2'
    row=index['properties']['records']['items'];row['properties']['annotation_summary']=obj({'count':count,'conflicts':count,'revision':digest})
    row['properties']['classification']=obj({'primary':array(category,6),'secondary':array(category,6),'alternative':array(category,6),'has_conflict':{'type':'boolean'}})
    row['required']=list(row['properties']);path.write_text(json.dumps(index,indent=2)+'\n')
    path=ROOT/'ontology/modules/public-enrichment-index.json';m=json.loads(path.read_text());m['projection_version']='CILE-PUBLIC-INDEX-2'
    old=m['schema_field_slots']
    m['schema_field_slots']={**mapping(index),**old}
    base='/properties/records/items/properties/'
    for field_path,slot in {'annotation_summary':'schema:hasPart','annotation_summary/properties/count':'public_annotation_count','annotation_summary/properties/conflicts':'public_annotation_conflicts','annotation_summary/properties/revision':'schema:version','classification':'extraction_framework','classification/properties/primary':'extraction_primary','classification/properties/secondary':'extraction_secondary','classification/properties/alternative':'extraction_alternative','classification/properties/has_conflict':'public_classification_conflict'}.items():m['schema_field_slots'][base+field_path]=slot
    m['counting_boundary']='Every active candidate counts once in the chosen register perimeter and revision. Classification roles are sets of explicit current public proposals; alternatives are excluded from class filters. Multiple primary classes or incompatible primary/secondary roles are retained conflicts, never silently selected. Manual annotation coverage is independent of extraction and completion.'
    path.write_text(json.dumps(m,indent=2)+'\n')


if __name__=='__main__':build()
