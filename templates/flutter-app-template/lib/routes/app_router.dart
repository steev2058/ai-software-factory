import 'package:flutter/material.dart';
import '../screens/login_screen.dart';
final appRouter = RouterConfig<Object>(routerDelegate: _SimpleRouterDelegate(), routeInformationParser: _SimpleParser());
class _SimpleParser extends RouteInformationParser<Object> { @override Future<Object> parseRouteInformation(RouteInformation routeInformation) async => Object(); }
class _SimpleRouterDelegate extends RouterDelegate<Object> with ChangeNotifier, PopNavigatorRouterDelegateMixin<Object> {
  @override final navigatorKey = GlobalKey<NavigatorState>();
  @override Widget build(BuildContext context) => Navigator(key: navigatorKey, pages: const [MaterialPage(child: LoginScreen())], onPopPage: (r,_)=>r.didPop(_));
  @override Future<void> setNewRoutePath(Object configuration) async {}
}
