# PytSite Object Document Mapper Plugin


## Changelog


### 6.5.2 (2019-04-18)

Initial default value of `field.DateTime` removed.


### 6.5.1 (2019-04-15)

Missing fields skip added in `MultiModelFinder`.


### 6.5 (2019-04-02)

Fields values history added. 


### 6.4.1 (2019-03-29)

Call order of `model.Entity._on_f_modified()` moved to `pre_save` stage. 


### 6.4 (2019-03-29)

- New hook method `model.Entity._on_f_modified()` added. 
- `reflect_prev_val` arg removed from `field.Base.set_val()`.


### 6.3 (2019-03-23)

New properties `minimum` and `maximum` added to `Integer` and `Decimal` 
fields.


### 6.2 (2019-03-21)

Support of multiple values of `model` property of `field.Ref` and 
`fieldRefsList`.


### 6.1 (2019-03-09)

New method `model.Entity.replace_field()` added.


### 6.0 (2019-03-04)

- `field.Abstract` class renamed to `Base`.
- `field.Base.required` prop renamed to `is_required`.
- `field.List.unique` prop renamed to `is_unique`.
- New method `field.Base.get_prev_val()` added.
- New args `skip_hooks` and `reflect_prev_val` added to 
  `field.Base.set_val()`.
- All `model.Entity` hook methods got prefix `on`. 
- `model.Entity._deleted()` hook method removed in favour of usage
  `_on_after_delete()` method.
- Default indexes added for `_created` and `_modified` fields of 
  `model.Entity`.
  

### 5.15.4 (2019-02-28)

Deletion hooks call order fixed.


### 5.15.3 (2019-02-28)

References checking fixed in `model.Entity.delete()`.


### 5.15.2 (2019-02-28)

Tracking of changes of entities' fields fixed #2.


### 5.15.1 (2019-02-28)

Tracking of changes of entities' fields fixed.


### 5.15 (2019-02-27)

New hook `model.Entity._deleted()`.


### 5.14 (2019-02-27)

New `model.Entity`'s hooks: `_created()` and `_modified()`.


### 5.13 (2019-02-21)

New properties in `model.Entity`: `is_saved`


### 5.12.1 (2019-02-20)

Missing reset of fields `is_modified` status fixed.


### 5.12 (2019-02-19)

- New property `field.Abstract.is_modified` added.
- New method `model.Entity.f_is_modified()` added.


### 5.11 (2019-02-19)

Support of `pytsite-8.11`.


### 5.10.4 (2019-02-19)

`field.Abstract.rst_val()` fixed.


### 5.10.3 (2019-02-19)

`field.Abstract.default` setter fixed.


### 5.10.2 (2019-01-28)

Fixed `Entity._depth` field definition.


### 5.10.1 (2019-01-28)

Overriding of `field.Integer.is_empty` removed.


### 5.10 (2019-01-23)

New `field.RefsList.model_cls` property added.


### 5.9 (2018-12-10)

New method `Finder.no_cache()` added.


### 5.8.1 (2018-12-10)

Unused obsolete `cache` arg removed from all `Finder`'s methods.


### 5.8 (2018-12-09)

New `Finder.rm()` method added.


### 5.7 (2018-12-06)

- Support of `pytsite-8.8` and `query-1.1`.
- New `mfind()` API function.
- `Finder` class separated in two classes: `SingleModelFinder` and
  `MultiModelFinder`.
- Support for multiple `model` arg's value in `field.Ref`.
- Finders result caching strategy improved.


### 5.6 (2018-12-06)

`Entity.http_api_*` hooks removed.


### 5.5.1 (2018-12-04)

`Entity.http_api_finder()` forbids operation by default.


### 5.5 (2018-12-04)

`http_api_finder()` and `http_api_get()` implemented in `Entity`.


### 5.4 (2018-11-25)

New kwarg `fast` added to `Entity.save()`.


### 5.3.1 (2018-11-07)

Entity DB data loading issue fixed.


### 5.3 (2018-11-07)

New attribute `storable` added to the `field.Abstract`.


### 5.2 (2018-11-05)

- `field.Abstract.on_entity_delete()` made private and got `entity`
  parameter.


### 5.1 (2018-11-03)

- New method `Entity.lang_package_name()` added.
- `Entity.get_package_name()` renamed to `package_name()`.
- `Entity.resolve_msg_id()` renamed to `resolve_lang_msg_id()`.



### 5.0 (2018-09-21)

Support of `pytsite-8.x`.


### 4.1 (2018-09-21)

New argument `force` in `Entity.delete()`.


### 4.0.3 (2018-09-21)

`get_by_ref()` fixed.


### 4.0.2 (2018-09-19)

`get_by_ref()` fixed.


### 4.0.1 (2018-09-17)

`get_by_ref()` fixed.


### 4.0 (2018-09-14)

- DBRefs removed in favour of manual refs.
- `error` module cleaned up.


### 3.7 (2018-09-07)

`strip_html` and `tidyfy_html` properties of the `field.String` are now
`True` by default.


### 3.6.2 (2018-09-02)

Exception usage fixed.


### 3.6.1 (2018-08-31)

Model checking fixed in `find()`.


### 3.6 (2018-08-28)

- Automatic referenced entities deletion detection added.
- New exception `InvalidReference` added.


### 3.5 (2018-07-29)

New argument `name` added to `Entity.define_index()`.


### 3.4 (2018-06-16)

- Properties added to `Aggregator`: `model`, `mock`, `pipeline`.
- `Aggregator` is iterable now.
- New `process` argument added to `Result.__init()__`.
- New `result_processor` argument added to `Finder.__init()__`.
- Colection names ends with 'y' letter building issue fixed.


### 3.3.1 (2018-06-03)

Finder argument sanitization fixed in some fields.


### 3.3 (2018-05-30)

Support of `pytsite-7.23`.


### 3.2 (2018-05-28)

`fields.Enum` changed:
  - `valid_values` property and contructor's argument renamed to
    `values`.
  - `valid_types` contructor's argument removed.


### 3.1 (2018-05-13)

Support of `pytsite-7.20`.


### 3.0 (2018-05-03)

- New API function: `clear_cache()`.
- Events related shortcut API functions added.
- `clear_finder_cache()` removed.
- `odm@register` event renamed to `odm@model.register`.
- `odm@finder_cache.clear` event renamed to `odm@cache.clear`.


### 2.1 (2018-04-25)

`_pre_save()` hook calling order shifted.


### 2.0.1 (2018-04-12)

Entity ID sanitizing added in `dispense()`.


### 2.0 (2018-04-06)

Query building logic moved to separate plugin named `query`.


### 1.10 (2018-03-24)

- `field.Abstract.get_raw_val()` renamed to
  `field.Abstract.get_storable_val()`.
- New hook method added: `field._on_get_storable()`.


### 1.9.2 (2018-03-05)

Entities relation check fixed


### 1.9.1 (2018-03-05)

Entities relation check fixed in `entity.children_count`.


### 1.9 (2018-03-05)

New properties: `Entity.children_count` and `Entity.has_children`.


### 1.8.1 (2018-03-05)

Relations check fixed.


### 1.8 (2018-03-01)

`Entity.parent` setter added.


### 1.7 (2018-03-01)

New API function: `reindex()`.


### 1.6.1 (2018-02-27)

Fields bugfix.


### 1.6 (2018-02-27)

- Support for nested entities added.
- Finder improved.
- Caching error fixed.


### 1.5 (2018-02-14)

- `Finder.__len__()` method added.
- `FinderResult` renamed to `Result`.
- `Entity` added to the public API.


### 1.4.6 (2018-02-13)

Non-blocking saving and deletion made blocking.


### 1.4.5 (2018-01-17)

Error in `field.ManualRef` fixed.


### 1.4.4 (2018-01-16)

Error in `resolve_manual_ref()` fixed.


### 1.4.3 (2018-01-15)

Finder cache management issue fixed.


### 1.4.2 (2018-01-13)

Finder cache management issue fixed.


### 1.4.1 (2018-01-13)

Registry key names fixed.


### 1.4 (2018-01-12)

- New fields added: `ObjectId`, `ManualRef`, `ManualRefsList`,
  `ManualRefsUniqueList`.
- New aggregation methods added: `sort()`, `limit()`.


### 1.3.1 (2018-01-04)

Entities cache initialization fixed.


### 1.3 (2018-01-02)

Events names refactoring.


### 1.2 (2017-12-13)

Support for `pytsite-7.0`.


### 1.1.3 (2017-12-08)

Init code fixed.


### 1.1.2 (2017-12-07)

Init code fixed.


### 1.1.1 (2017-12-04)

Support for caching subsystem changes of `pytsite-6.1`.


### 1.1 (2017-12-02)

Support for `pytsite-6.1`.


### 1.0 (2017-11-25)

First release.
