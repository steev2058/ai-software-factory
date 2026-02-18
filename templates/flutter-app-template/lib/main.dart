import 'package:flutter/material.dart';
import 'routes/app_router.dart';
void main() => runApp(const MyApp());
class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp.router(routerConfig: appRouter);
}
